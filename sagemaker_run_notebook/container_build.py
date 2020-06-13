# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import argparse
import os
import shutil
import sys
import tempfile
import time
import zipfile

import boto3

import sagemaker_run_notebook.utils as utils

default_base = "python:3.7-slim-buster"


def create_project(repo_name, role, zipfile, base_image=default_base):
    session = boto3.session.Session()
    client = session.client("codebuild")

    region = session.region_name
    sts = session.client("sts")
    identity = sts.get_caller_identity()
    account = identity["Account"]
    args = {
        "name": f"create-sagemaker-container-{repo_name}",
        "description": f"Build the container {repo_name} for running notebooks in SageMaker",
        "source": {"type": "S3", "location": zipfile},
        "artifacts": {"type": "NO_ARTIFACTS"},
        "environment": {
            "type": "LINUX_CONTAINER",
            "image": "aws/codebuild/standard:4.0",
            "computeType": "BUILD_GENERAL1_SMALL",
            "environmentVariables": [
                {"name": "AWS_DEFAULT_REGION", "value": region},
                {"name": "AWS_ACCOUNT_ID", "value": account},
                {"name": "IMAGE_REPO_NAME", "value": repo_name},
                {"name": "IMAGE_TAG", "value": "latest"},
                {"name": "BASE_IMAGE", "value": base_image},
            ],
            "privilegedMode": True,
        },
        "serviceRole": f"arn:aws:iam::{account}:role/{role}",
    }

    response = client.create_project(**args)
    return response


def delete_project(repo_name):
    session = boto3.session.Session()
    client = session.client("codebuild")

    response = client.delete_project(name=f"create-sagemaker-container-{repo_name}")
    return response


def start_build(repo_name):
    args = {"projectName": f"create-sagemaker-container-{repo_name}"}
    session = boto3.session.Session()
    client = session.client("codebuild")

    response = client.start_build(**args)
    return response["build"]["id"]


def wait_for_build(id, poll_seconds=10):
    session = boto3.session.Session()
    client = session.client("codebuild")
    status = client.batch_get_builds(ids=[id])
    first = True
    while status["builds"][0]["buildStatus"] == "IN_PROGRESS":
        if not first:
            print(".", end="")
            sys.stdout.flush()
        first = False
        time.sleep(poll_seconds)
        status = client.batch_get_builds(ids=[id])
    print()
    print(f"Build complete, status = {status['builds'][0]['buildStatus']}")
    print(f"Logs at {status['builds'][0]['logs']['deepLink']}")


def upload_zip_file(repo_name, bucket, dir="."):
    if not bucket:
        bucket = utils.default_bucket()

    key = f"codebuild-sagemaker-container-{repo_name}.zip"
    origdir = os.getcwd()
    os.chdir(dir)
    try:
        with tempfile.TemporaryFile() as tmp:
            with zipfile.ZipFile(tmp, "w") as zip:
                for dirname, _, filelist in os.walk("."):
                    for file in filelist:
                        zip.write(f"{dirname}/{file}")
            tmp.seek(0)
            s3 = boto3.session.Session().client("s3")
            s3.upload_fileobj(tmp, bucket, key)
        return (bucket, key)
    finally:
        os.chdir(origdir)


def delete_zip_file(bucket, key):
    s3 = boto3.session.Session().client("s3")
    s3.delete_object(Bucket=bucket, Key=key)


def create_container(repo_name, role, bucket, base, requirements):
    container_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "container"
    )
    with tempfile.TemporaryDirectory() as td:
        dest_dir = os.path.join(td, "container")
        shutil.copytree(container_dir, dest_dir)
        if requirements:
            shutil.copy2(requirements, os.path.join(dest_dir, "requirements.txt"))
        bucket, key = upload_zip_file(repo_name, bucket, dir=dest_dir)
    try:
        create_project(repo_name, role, zipfile=f"{bucket}/{key}", base_image=base)
        try:
            id = start_build(repo_name)
            wait_for_build(id)
        finally:
            delete_project(repo_name)
    finally:
        delete_zip_file(bucket, key)
