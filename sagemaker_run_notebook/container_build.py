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
import collections
import functools
import os
import shutil
import sys
import tempfile
import time
import zipfile

import boto3
import botocore.config
from botocore.exceptions import ClientError

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


class LogState(object):
    STARTING = 1
    WAIT_IN_PROGRESS = 2
    TAILING = 3
    JOB_COMPLETE = 4
    COMPLETE = 5


# Position is a tuple that includes the last read timestamp and the number of items that were read
# at that time. This is used to figure out which event to start with on the next read.
Position = collections.namedtuple("Position", ["timestamp", "skip"])


def log_stream(client, log_group, stream_name, position):
    """A generator for log items in a single stream. This will yield all the
    items that are available at the current moment.

    Args:
        client (boto3.CloudWatchLogs.Client): The Boto client for CloudWatch logs.
        log_group (str): The name of the log group.
        stream_name (str): The name of the specific stream.
        position (Position): A tuple with the time stamp value to start reading the logs from and
                             The number of log entries to skip at the start. This is for when
                             there are multiple entries at the same timestamp.
        start_time (int): The time stamp value to start reading the logs from (default: 0).
        skip (int): The number of log entries to skip at the start (default: 0). This is for when there are
                    multiple entries at the same timestamp.

    Yields:
        A tuple with:
        dict: A CloudWatch log event with the following key-value pairs:
             'timestamp' (int): The time of the event.
             'message' (str): The log event data.
             'ingestionTime' (int): The time the event was ingested.
        Position: The new position
    """

    start_time, skip = position
    next_token = None

    event_count = 1
    while event_count > 0:
        if next_token is not None:
            token_arg = {"nextToken": next_token}
        else:
            token_arg = {}

        response = client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            startTime=start_time,
            startFromHead=True,
            **token_arg,
        )
        next_token = response["nextForwardToken"]
        events = response["events"]
        event_count = len(events)
        if event_count > skip:
            events = events[skip:]
            skip = 0
        else:
            skip = skip - event_count
            events = []
        for ev in events:
            ts, count = position
            if ev["timestamp"] == ts:
                position = Position(timestamp=ts, skip=count + 1)
            else:
                position = Position(timestamp=ev["timestamp"], skip=1)
            yield ev, position


# Copy/paste/slight mods from session.logs_for_job() in the SageMaker Python SDK
def logs_for_build(
    build_id, wait=False, poll=10, session=None
):  # noqa: C901 - suppress complexity warning for this method
    """Display the logs for a given build, optionally tailing them until the
    build is complete.

    Args:
        build_id (str): The ID of the build to display the logs for.
        wait (bool): Whether to keep looking for new log entries until the build completes (default: False).
        poll (int): The interval in seconds between polling for new log entries and build completion (default: 10).
        session (boto3.session.Session): A boto3 session to use (default: create a new one).

    Raises:
        ValueError: If waiting and the build fails.
    """

    session = utils.ensure_session(session)
    codebuild = session.client("codebuild")
    description = codebuild.batch_get_builds(ids=[build_id])["builds"][0]
    status = description["buildStatus"]

    log_group = description["logs"].get("groupName")
    stream_name = description["logs"].get("streamName")  # The list of log streams
    position = Position(
        timestamp=0, skip=0
    )  # The current position in each stream, map of stream name -> position

    # Increase retries allowed (from default of 4), as we don't want waiting for a build
    # to be interrupted by a transient exception.
    config = botocore.config.Config(retries={"max_attempts": 15})
    client = session.client("logs", config=config)

    job_already_completed = False if status == "IN_PROGRESS" else True

    state = (
        LogState.STARTING if wait and not job_already_completed else LogState.COMPLETE
    )
    dot = True

    while state == LogState.STARTING and log_group == None:
        time.sleep(poll)
        description = codebuild.batch_get_builds(ids=[build_id])["builds"][0]
        log_group = description["logs"].get("groupName")
        stream_name = description["logs"].get("streamName")

    if state == LogState.STARTING:
        state = LogState.TAILING

    # The loop below implements a state machine that alternates between checking the build status and
    # reading whatever is available in the logs at this point. Note, that if we were called with
    # wait == False, we never check the job status.
    #
    # If wait == TRUE and job is not completed, the initial state is STARTING
    # If wait == FALSE, the initial state is COMPLETE (doesn't matter if the job really is complete).
    #
    # The state table:
    #
    # STATE               ACTIONS                        CONDITION               NEW STATE
    # ----------------    ----------------               -------------------     ----------------
    # STARTING            Pause, Get Status              Valid LogStream Arn     TAILING
    #                                                    Else                    STARTING
    # TAILING             Read logs, Pause, Get status   Job complete            JOB_COMPLETE
    #                                                    Else                    TAILING
    # JOB_COMPLETE        Read logs, Pause               Any                     COMPLETE
    # COMPLETE            Read logs, Exit                                        N/A
    #
    # Notes:
    # - The JOB_COMPLETE state forces us to do an extra pause and read any items that got to Cloudwatch after
    #   the build was marked complete.
    last_describe_job_call = time.time()
    dot_printed = False
    while True:
        for event, position in log_stream(client, log_group, stream_name, position):
            print(event["message"].rstrip())
            if dot:
                dot = False
                if dot_printed:
                    print()
        if state == LogState.COMPLETE:
            break

        time.sleep(poll)
        if dot:
            print(".", end="")
            sys.stdout.flush()
            dot_printed = True
        if state == LogState.JOB_COMPLETE:
            state = LogState.COMPLETE
        elif time.time() - last_describe_job_call >= 30:
            description = codebuild.batch_get_builds(ids=[build_id])["builds"][0]
            status = description["buildStatus"]

            last_describe_job_call = time.time()

            status = description["buildStatus"]

            if status != "IN_PROGRESS":
                print()
                state = LogState.JOB_COMPLETE

    if wait:
        if dot:
            print()


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


def create_container(
    repo_name, role, bucket, base, requirements, script, kernel, log=True
):
    container_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "container"
    )
    with tempfile.TemporaryDirectory() as td:
        dest_dir = os.path.join(td, "container")
        shutil.copytree(container_dir, dest_dir)
        if requirements:
            shutil.copy2(requirements, os.path.join(dest_dir, "requirements.txt"))
        if script:
            shutil.copy2(script, os.path.join(dest_dir, "init-script.sh"))
        if kernel:
            with open(os.path.join(dest_dir, "kernel-var.txt"), "w") as f:
                print(kernel, file=f)
        bucket, key = upload_zip_file(repo_name, bucket, dir=dest_dir)
    try:
        create_project(repo_name, role, zipfile=f"{bucket}/{key}", base_image=base)
        try:
            id = start_build(repo_name)
            if log:
                logs_for_build(id, wait=True)
            else:
                wait_for_build(id)
        finally:
            delete_project(repo_name)
    finally:
        delete_zip_file(bucket, key)
