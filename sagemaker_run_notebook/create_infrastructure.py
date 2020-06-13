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

import os
import sys
import time

import botocore.exceptions
import boto3

cfn_template_file = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "cloudformation.yml"
)


def ensure_session(session=None):
    """If session is None, create a default session and return it. Otherwise return the session passed in"""
    if session is None:
        session = boto3.session.Session()
    return session


def wait_for_infrastructure(stack_id, progress=True, sleep_time=10, session=None):
    session = ensure_session(session)
    client = session.client("cloudformation")
    done = False
    while not done:
        if progress:
            print(".", end="")
            sys.stdout.flush()
        desc = client.describe_stacks(StackName=stack_id)["Stacks"][0]
        status = desc["StackStatus"]
        if "IN_PROGRESS" not in status:
            done = True
        else:
            time.sleep(sleep_time)
    if progress:
        print()
    return status, desc.get("StackStatusReason")


def create_infrastructure(session=None, update=False, wait=True):
    with open(cfn_template_file, mode="r") as f:
        cfn_template = f.read()
    session = ensure_session(session)
    client = session.client("cloudformation")

    try:
        if not update:
            response = client.create_stack(
                StackName="sagemaker-run-notebook",
                TemplateBody=cfn_template,
                Capabilities=["CAPABILITY_NAMED_IAM"],
            )
        else:
            response = client.update_stack(
                StackName="sagemaker-run-notebook",
                TemplateBody=cfn_template,
                Capabilities=["CAPABILITY_NAMED_IAM"],
            )
    except botocore.exceptions.ClientError as ce:
        if ce.response["Error"]["Code"] == "AlreadyExistsException":
            print(
                "The infrastructure has already been created. Use update to update it."
            )
            return
        elif ce.response["Error"][
            "Code"
        ] == "ValidationError" and "No updates are to be performed" in str(ce):
            print("The infrastructure is already up-to-date. No work to do.")
            return
        raise

    stack_id = response["StackId"]
    print(f"Creating cloudformation stack {stack_id}")
    if not wait:
        return
    status, reason = wait_for_infrastructure(stack_id, session=session)
    if status not in ["CREATE_COMPLETE", "UPDATE_COMPLETE"]:
        print(f"Unexpected result state {status}. Reason is {reason}")
    else:
        print("Stack successfully created")
