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

import re

import boto3
import botocore

_default_bucket = None
_default_bucket_name_override = None

# Utility functions that are copied and pasted from the SageMaker Python SDK so that we
# don't need to include that and all its dependencies.
def default_bucket(session=None):
    """Return the name of the default bucket to use in relevant Amazon SageMaker interactions.

    Returns:
        str: The name of the default bucket, which is of the form:
            ``sagemaker-{region}-{AWS account ID}``.
    """
    global _default_bucket
    global _default_bucket_name_override

    if _default_bucket:
        return _default_bucket

    session = ensure_session(session)
    region = session.region_name

    default_bucket = _default_bucket_name_override
    if not default_bucket:
        account = session.client(
            "sts", region_name=region, endpoint_url=sts_regional_endpoint(region)
        ).get_caller_identity()["Account"]
        default_bucket = "sagemaker-{}-{}".format(region, account)

    _create_s3_bucket_if_it_does_not_exist(
        bucket_name=default_bucket, region=region, session=session
    )

    _default_bucket = default_bucket

    return default_bucket


def _create_s3_bucket_if_it_does_not_exist(bucket_name, region, session):
    """Creates an S3 Bucket if it does not exist.
    Also swallows a few common exceptions that indicate that the bucket already exists or
    that it is being created.

    Args:
        bucket_name (str): Name of the S3 bucket to be created.
        region (str): The region in which to create the bucket.

    Raises:
        botocore.exceptions.ClientError: If S3 throws an unexpected exception during bucket
            creation.
            If the exception is due to the bucket already existing or
            already being created, no exception is raised.

    """
    bucket = session.resource("s3", region_name=region).Bucket(name=bucket_name)
    if bucket.creation_date is None:
        try:
            s3 = session.resource("s3", region_name=region)
            if region == "us-east-1":
                # 'us-east-1' cannot be specified because it is the default region:
                # https://github.com/boto/boto3/issues/125
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": region},
                )

            print("Created S3 bucket: %s", bucket_name)
        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            message = e.response["Error"]["Message"]

            if error_code == "BucketAlreadyOwnedByYou":
                pass
            elif (
                error_code == "OperationAborted"
                and "conflicting conditional operation" in message
            ):
                # If this bucket is already being concurrently created, we don't need to create
                # it again.
                pass
            else:
                raise


def sts_regional_endpoint(region):
    """Get the AWS STS endpoint specific for the given region.

    We need this function because the AWS SDK does not yet honor
    the ``region_name`` parameter when creating an AWS STS client.

    For the list of regional endpoints, see
    https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_enable-regions.html#id_credentials_region-endpoints.

    Args:
        region (str): AWS region name

    Returns:
        str: AWS STS regional endpoint
    """
    domain = _domain_for_region(region)
    return "https://sts.{}.{}".format(region, domain)


def _domain_for_region(region):
    """Get the DNS suffix for the given region.

    Args:
        region (str): AWS region name

    Returns:
        str: the DNS suffix
    """
    return "c2s.ic.gov" if region == "us-iso-east-1" else "amazonaws.com"


def get_execution_role(session):
    """Return the role ARN whose credentials are used to call the API.
    Throws an exception if the current AWS identity is not a role.

    Returns:
        (str): The role ARN
    """
    assumed_role = session.client("sts").get_caller_identity()["Arn"]
    if ":user/" in assumed_role:
        user_name = assumed_role[assumed_role.rfind("/") + 1 :]
        raise ValueError(
            f"You are running as the IAM user '{user_name}'. You must supply an IAM role to run SageMaker jobs."
        )

    if "AmazonSageMaker-ExecutionRole" in assumed_role:
        role = re.sub(
            r"^(.+)sts::(\d+):assumed-role/(.+?)/.*$",
            r"\1iam::\2:role/service-role/\3",
            assumed_role,
        )
        return role

    role = re.sub(
        r"^(.+)sts::(\d+):assumed-role/(.+?)/.*$", r"\1iam::\2:role/\3", assumed_role
    )

    # Call IAM to get the role's path
    role_name = role[role.rfind("/") + 1 :]
    arn = session.client("iam").get_role(RoleName=role_name)["Role"]["Arn"]

    if ":role/" in arn:
        return arn
    message = "The current AWS identity is not a role: {}, therefore it cannot be used as a SageMaker execution role"
    raise ValueError(message.format(arn))


def ensure_session(session=None):
    """If session is None, create a default session and return it. Otherwise return the session passed in"""
    if session is None:
        session = boto3.session.Session()
    return session
