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
"""Run a notebook on demand or on a schedule using Amazon SageMaker Processing Jobs"""

import asyncio
import errno
import io
import logging
import json
import os
import re
import time
from subprocess import Popen, PIPE, STDOUT, DEVNULL
from shlex import split
import zipfile as zip

import botocore
import boto3

from .utils import default_bucket, get_execution_role

abbrev_image_pat = re.compile(
    r"(?P<account>\d+).dkr.ecr.(?P<region>[^.]+).amazonaws.com/(?P<image>[^:/]+)(?P<tag>:[^:]+)?"
)


def abbreviate_image(image):
    """If the image belongs to this account, just return the base name"""
    m = abbrev_image_pat.fullmatch(image)
    if m:
        tag = m.group("tag")
        if tag == None or tag == ":latest":
            tag = ""
        return m.group("image") + tag
    else:
        return image


abbrev_role_pat = re.compile(r"arn:aws:iam::(?P<account>\d+):role/(?P<name>[^/]+)")


def abbreviate_role(role):
    """If the role belongs to this account, just return the base name"""
    m = abbrev_role_pat.fullmatch(role)
    if m:
        return m.group("name")
    else:
        return role


def upload_notebook(notebook, session=None):
    """Uploads a notebook to S3 in the default SageMaker Python SDK bucket for
    this user. The resulting S3 object will be named "s3://<bucket>/papermill-input/notebook-YYYY-MM-DD-hh-mm-ss.ipynb".

    Args:
      notebook (str):
        The filename of the notebook you want to upload. (Required)
      session (boto3.Session):
        A boto3 session to use. Will create a default session if not supplied. (Default: None)

    Returns:
      The resulting object name in S3 in URI format.
    """
    with open(notebook, "rb") as f:
        return upload_fileobj(f, session)


def upload_fileobj(notebook_fileobj, session=None):
    """Uploads a file object to S3 in the default SageMaker Python SDK bucket for
    this user. The resulting S3 object will be named "s3://<bucket>/papermill-input/notebook-YYYY-MM-DD-hh-mm-ss.ipynb".

    Args:
      notebook_fileobj (fileobj):
        A file object (as returned from open) that is reading from the notebook you want to upload. (Required)
      session (boto3.Session):
        A boto3 session to use. Will create a default session if not supplied. (Default: None)

    Returns:
      The resulting object name in S3 in URI format.
    """

    session = ensure_session(session)
    snotebook = "notebook-{}.ipynb".format(
        time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
    )

    s3 = session.client("s3")
    key = "papermill_input/" + snotebook
    bucket = default_bucket(session)
    s3path = "s3://{}/{}".format(bucket, key)
    s3.upload_fileobj(notebook_fileobj, bucket, key)

    return s3path


def get_output_prefix():
    """Returns an S3 prefix in the Python SDK default bucket."""
    return "s3://{}/papermill_output".format(default_bucket())


def execute_notebook(
    *,
    image,
    input_path,
    output_prefix,
    notebook,
    parameters,
    role=None,
    instance_type,
    session,
):
    session = ensure_session(session)

    if not role:
        role = get_execution_role(session)
    elif "/" not in role:
        account = session.client("sts").get_caller_identity()["Account"]
        role = "arn:aws:iam::{}:role/{}".format(account, role)

    if "/" not in image:
        account = session.client("sts").get_caller_identity()["Account"]
        region = session.region_name
        image = "{}.dkr.ecr.{}.amazonaws.com/{}:latest".format(account, region, image)

    if notebook == None:
        notebook = input_path

    base = os.path.basename(notebook)
    nb_name, nb_ext = os.path.splitext(base)
    timestamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())

    job_name = (
        ("papermill-" + re.sub(r"[^-a-zA-Z0-9]", "-", nb_name))[: 62 - len(timestamp)]
        + "-"
        + timestamp
    )
    input_directory = "/opt/ml/processing/input/"
    local_input = input_directory + os.path.basename(input_path)
    result = "{}-{}{}".format(nb_name, timestamp, nb_ext)
    local_output = "/opt/ml/processing/output/"

    api_args = {
        "ProcessingInputs": [
            {
                "InputName": "notebook",
                "S3Input": {
                    "S3Uri": input_path,
                    "LocalPath": input_directory,
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File",
                    "S3DataDistributionType": "FullyReplicated",
                },
            },
        ],
        "ProcessingOutputConfig": {
            "Outputs": [
                {
                    "OutputName": "result",
                    "S3Output": {
                        "S3Uri": output_prefix,
                        "LocalPath": local_output,
                        "S3UploadMode": "EndOfJob",
                    },
                },
            ],
        },
        "ProcessingJobName": job_name,
        "ProcessingResources": {
            "ClusterConfig": {
                "InstanceCount": 1,
                "InstanceType": instance_type,
                "VolumeSizeInGB": 40,
            }
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": 7200},
        "AppSpecification": {
            "ImageUri": image,
            "ContainerArguments": [
                "run_notebook",
            ],
        },
        "RoleArn": role,
        "Environment": {},
    }

    api_args["Environment"]["PAPERMILL_INPUT"] = local_input
    api_args["Environment"]["PAPERMILL_OUTPUT"] = local_output + result
    if os.environ.get("AWS_DEFAULT_REGION") != None:
        api_args["Environment"]["AWS_DEFAULT_REGION"] = os.environ["AWS_DEFAULT_REGION"]
    api_args["Environment"]["PAPERMILL_PARAMS"] = json.dumps(parameters)
    api_args["Environment"]["PAPERMILL_NOTEBOOK_NAME"] = notebook

    client = boto3.client("sagemaker")
    result = client.create_processing_job(**api_args)
    job_arn = result["ProcessingJobArn"]
    job = re.sub("^.*/", "", job_arn)
    return job


def wait_for_complete(job_name, progress=True, sleep_time=10, session=None):
    """Wait for a notebook execution job to complete.

    Args:
      job_name (str):
        The name of the SageMaker Processing Job executing the notebook. (Required)
      progress (boolean):
        If True, print a period after every poll attempt. (Default: True)
      sleep_time (int):
        The number of seconds between polls. (Default: 10)
      session (boto3.Session):
        A boto3 session to use. Will create a default session if not supplied. (Default: None)

    Returns:
      A tuple with the job status and the failure message if any.
    """

    session = ensure_session(session)
    client = session.client("sagemaker")
    done = False
    while not done:
        if progress:
            print(".", end="")
        desc = client.describe_processing_job(ProcessingJobName=job_name)
        status = desc["ProcessingJobStatus"]
        if status != "InProgress":
            done = True
        else:
            time.sleep(sleep_time)
    if progress:
        print()
    return status, desc.get("FailureReason")


def download_notebook(job_name, output=".", session=None):
    """Download the output notebook from a previously completed job.

    Args:
      job_name (str): The name of the SageMaker Processing Job that executed the notebook. (Required)
      output (str): The directory to copy the output file to. (Default: the current working directory)
      session (boto3.Session):
        A boto3 session to use. Will create a default session if not supplied. (Default: None)

    Returns:
      The filename of the downloaded notebook.
    """
    session = ensure_session(session)
    client = session.client("sagemaker")
    desc = client.describe_processing_job(ProcessingJobName=job_name)

    prefix = desc["ProcessingOutputConfig"]["Outputs"][0]["S3Output"]["S3Uri"]
    notebook = os.path.basename(desc["Environment"]["PAPERMILL_OUTPUT"])
    s3path = "{}/{}".format(prefix, notebook)

    if not os.path.exists(output):
        try:
            os.makedirs(output)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    p1 = Popen(split("aws s3 cp --no-progress {} {}/".format(s3path, output)))
    p1.wait()
    return "{}/{}".format(output.rstrip("/"), notebook)


def run_notebook(
    image,
    notebook,
    parameters={},
    role=None,
    instance_type="ml.m5.large",
    output_prefix=None,
    output=".",
    session=None,
):
    """Run a notebook in SageMaker Processing producing a new output notebook.

    Args:
        image (str): The ECR image that defines the environment to run the job (required).
        notebook (str): The local notebook to upload and run (required).
        parameters (dict): The dictionary of parameters to pass to the notebook (default: {}).
        role (str): The name of a role to use to run the notebook (default: calls get_execution_role()).
        instance_type (str): The SageMaker instance to use for executing the job (default: ml.m5.large).
        output_prefix (str): The prefix path in S3 for where to store the output notebook
                             (default: determined based on SageMaker Python SDK)
        output (str): The directory to copy the output file to (default: the current working directory).
        session (boto3.Session): The boto3 session to use. Will create a default session if not supplied (default: None).

    Returns:
        A tuple with the processing job name, the job status, the failure reason (or None) and the the path to
        the result notebook. The output notebook name is formed by adding a timestamp to the original notebook name.
    """
    session = ensure_session(session)
    if output_prefix is None:
        output_prefix = get_output_prefix()
    s3path = upload_notebook(notebook, session)
    job_name = execute_notebook(
        image=image,
        input_path=s3path,
        output_prefix=output_prefix,
        notebook=notebook,
        parameters=parameters,
        role=role,
        instance_type=instance_type,
        session=session,
    )
    print("Job {} started".format(job_name))
    status, failure_reason = wait_for_complete(job_name)
    if status == "Completed":
        local = download_notebook(job_name, output=output)
    else:
        local = None
    return (job_name, status, local, failure_reason)


def stop_run(job_name, session=None):
    """Stop the named processing job

    Args:
       job_name (string): The name of the job to stop
       session (boto3.Session): The boto3 session to use. Will create a default session if not supplied (default: None)."""
    session = ensure_session(session)
    client = session.client("sagemaker")
    client.stop_processing_job(ProcessingJobName=job_name)


def describe_runs(n=0, notebook=None, rule=None, session=None):
    """Returns a generator of descriptions for all the notebook runs. See :meth:`describe_run` for details of
    the description.

    Args:
       n (int): The number of runs to return or all runs if 0 (default: 0)
       notebook (str): If not None, return only runs of this notebook (default: None)
       rule (str): If not None, return only runs invoked by this rule (default: None)
       session (boto3.Session): The boto3 session to use. Will create a default session if not supplied (default: None).
    """
    session = ensure_session(session)
    client = session.client("sagemaker")
    paginator = client.get_paginator("list_processing_jobs")
    page_iterator = paginator.paginate(NameContains="papermill-")

    for page in page_iterator:
        for item in page["ProcessingJobSummaries"]:
            job_name = item["ProcessingJobName"]
            if not job_name.startswith("papermill-"):
                continue
            d = describe_run(job_name, session)

            if notebook != None and notebook != d["Notebook"]:
                continue
            if rule != None and rule != d["Rule"]:
                continue
            yield d

            if n > 0:
                n = n - 1
                if n == 0:
                    return


def describe_run(job_name, session=None):
    """Describe a particular notebook run.

    Args:
     job_name (str): The name of the processing job that ran the notebook.

    Returns:
      A dictionary with keys for each element of the job description. For example::

      {'Notebook': 'scala-spark-test.ipynb',
       'Rule': '',
       'Parameters': '{"input": "s3://notebook-testing/const.txt"}',
       'Job': 'papermill-scala-spark-test-2020-10-21-20-00-11',
       'Status': 'Completed',
       'Failure': None,
       'Created': datetime.datetime(2020, 10, 21, 13, 0, 12, 817000, tzinfo=tzlocal()),
       'Start': datetime.datetime(2020, 10, 21, 13, 4, 1, 58000, tzinfo=tzlocal()),
       'End': datetime.datetime(2020, 10, 21, 13, 4, 55, 710000, tzinfo=tzlocal()),
       'Elapsed': datetime.timedelta(seconds=54, microseconds=652000),
       'Result': 's3://sagemaker-us-west-2-1234567890/papermill_output/scala-spark-test-2020-10-21-20-00-11.ipynb',
       'Input': 's3://sagemaker-us-west-2-1234567890/papermill_input/notebook-2020-10-21-20-00-08.ipynb',
       'Image': 'spark-scala-notebook-runner',
       'Instance': 'ml.m5.large',
       'Role': 'BasicExecuteNotebookRole-us-west-2'}
    """
    session = ensure_session(session)
    client = session.client("sagemaker")

    while True:
        try:
            desc = client.describe_processing_job(ProcessingJobName=job_name)
            break
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ThrottlingException":
                time.sleep(1)
            else:
                raise e

    status = desc["ProcessingJobStatus"]
    if status == "Completed":
        output_prefix = desc["ProcessingOutputConfig"]["Outputs"][0]["S3Output"][
            "S3Uri"
        ]
        notebook_name = os.path.basename(desc["Environment"]["PAPERMILL_OUTPUT"])
        result = "{}/{}".format(output_prefix, notebook_name)
    else:
        result = None

    if status == "Failed":
        failure = desc["FailureReason"]
    else:
        failure = None

    d = {}
    d["Notebook"] = desc["Environment"].get("PAPERMILL_NOTEBOOK_NAME", "")
    d["Rule"] = desc["Environment"].get("AWS_EVENTBRIDGE_RULE", "")
    d["Parameters"] = desc["Environment"].get("PAPERMILL_PARAMS", "")
    d["Job"] = job_name
    d["Status"] = status
    d["Failure"] = failure
    d["Created"] = desc["CreationTime"]
    d["Start"] = desc.get("ProcessingStartTime")
    d["End"] = desc.get("ProcessingEndTime")
    elapsed = None
    if d.get("Start") is not None and d.get("End") is not None:
        elapsed = d["End"] - d["Start"]
    d["Elapsed"] = elapsed
    d["Result"] = result
    d["Input"] = desc["ProcessingInputs"][0]["S3Input"]["S3Uri"]
    d["Image"] = abbreviate_image(desc["AppSpecification"]["ImageUri"])
    d["Instance"] = desc["ProcessingResources"]["ClusterConfig"]["InstanceType"]
    d["Role"] = abbreviate_role(desc["RoleArn"])

    return d


def expand_params(params):
    try:
        param_map = json.loads(params)
        return ", ".join([f"{p}={v}" for p, v in param_map.items()])
    except Exception:
        return ""


class NewJobs:
    def __init__(self, client):
        self.client = client
        self.latest_seen_job = None
        self.next_latest_seen_job = None

    async def get_new(self):
        next_token = None
        if self.next_latest_seen_job != None:
            self.latest_seen_job = self.next_latest_seen_job
            self.next_latest_seen_job = None
        while True:
            args = {"NextToken": next_token} if next_token else {}
            while True:
                try:
                    await asyncio.sleep(0)
                    result = self.client.list_processing_jobs(MaxResults=30, **args)
                    break
                except botocore.exceptions.ClientError as e:
                    if e.response["Error"]["Code"] == "ThrottlingException":
                        time.sleep(1)
                    else:
                        raise e
            jobs = result["ProcessingJobSummaries"]
            for job in jobs:
                if not self.next_latest_seen_job:
                    self.next_latest_seen_job = job["ProcessingJobName"]
                if job["ProcessingJobName"] == self.latest_seen_job:
                    return
                yield job
            next_token = result.get("NextToken")
            if not next_token:
                break


class NotebookRunTracker:
    """
    NotebookRunTracker keeps track of many recent running jobs and optimizes the number of boto calls
    you're doing to get the status by remembering previous runs and knowing that only in progress jobs can
    change status (and therefore need to be polled).
    """

    # We store the list backwards from how it's viewed outside so that we can just append new jobs on
    # the end.
    def __init__(self, max_jobs=20, session=None, log=None):
        self.session = ensure_session(session)
        self.client = self.session.client("sagemaker")
        self.log = log or logging.getLogger(__name__)
        self.max_jobs = max_jobs

        self.new_jobs = NewJobs(self.client)
        self.run_list = []
        self.in_progress = {}

    def __getitem__(self, item):
        return self.run_list[::-1][item]

    def __len__(self):
        return len(self.run_list)

    async def update_list(self):
        list_count = 0
        new_runs = []
        async for job in self.new_jobs.get_new():
            job_name = job["ProcessingJobName"]
            if not job_name.startswith("papermill-"):
                continue
            await asyncio.sleep(0)
            self.log.debug(f"Describing new job: {job_name}")
            desc = describe_run(job_name, session=self.session)
            new_runs.append(desc)
            if desc["Status"] == "InProgress" or desc["Status"] == "Stopping":
                self.in_progress[job_name] = desc
            list_count += 1
            if list_count >= self.max_jobs:
                break
        self.run_list.extend(new_runs[::-1])
        if len(self.run_list) > self.max_jobs:
            trimlen = len(self.run_list) - self.max_jobs
            for r in self.run_list[:trimlen]:
                if r["Status"] == "InProgress" or r["Status"] == "Stopping":
                    if r["Job"] in self.in_progress:
                        del self.in_progress[r["Job"]]
            self.run_list = self.run_list[trimlen:]

    async def update_in_progress(self):
        for job, desc in list(self.in_progress.items()):
            await asyncio.sleep(0)
            self.log.debug(f"Describing in progress job: {job}")
            new_desc = describe_run(job, session=self.session)
            desc["Status"] = new_desc["Status"]
            desc["Failure"] = new_desc["Failure"]
            desc["Start"] = new_desc["Start"]
            desc["End"] = new_desc["End"]
            desc["Elapsed"] = new_desc["Elapsed"]
            desc["Result"] = new_desc["Result"]

            if not (
                new_desc["Status"] == "InProgress" or new_desc["Status"] == "Stopping"
            ):
                if (
                    job in self.in_progress
                ):  # because of the asyncio it's posssible for us to race here
                    del self.in_progress[job]

    async def update(self):
        await self.update_list()
        await self.update_in_progress()


def list_runs(n=0, notebook=None, rule=None, session=None):
    """Returns a pandas data frame of the runs, with the most recent at the top.

    Args:
        n (int): The number of runs to return or all runs if 0 (default: 0)
        notebook (str): If not None, return only runs of this notebook (default: None)
        rule (str): If not None, return only runs invoked by this rule (default: None)
        session (boto3.Session): The boto3 session to use. Will create a default session if not supplied (default: None).
    """
    import pandas as pd  # pylint: disable=import-error

    df = pd.DataFrame(describe_runs(n=n, notebook=notebook, rule=rule, session=session))
    df["Parameters"] = df["Parameters"].map(expand_params)
    return df


def download_all(lis, output=".", session=None):
    """Download each of the output notebooks from a list previously completed jobs.

    Args:
      lis (list, pandas.Series, or pandas.DataFrame): A list of jobs or a pandas DataFrame with a "Job" column (as returned by :meth:`list_runs`). (Required)
      output (str): The directory to copy the output files to. (Default: the current working directory)
      session (boto3.Session):
        A boto3 session to use. Will create a default session if not supplied. (Default: None)

    Returns:
      The list of the filenames of the downloaded notebooks.
    """
    import pandas as pd  # pylint: disable=import-error

    if isinstance(lis, pd.DataFrame):
        lis = list(lis["Job"])
    elif isinstance(lis, pd.Series):
        lis = list(lis)

    session = ensure_session(session)
    return [download_notebook(job, output, session) for job in lis]


def ensure_session(session=None):
    """If session is None, create a default session and return it. Otherwise return the session passed in"""
    if session is None:
        session = boto3.session.Session()
    return session


code_file = "lambda_function.py"
lambda_function_name = "RunNotebook"
lambda_description = (
    "A function to run Jupyter notebooks using SageMaker processing jobs"
)


def create_lambda(role=None, session=None):
    session = ensure_session(session)
    created = False

    if role is None:
        print(
            "No role specified, will create a minimal role and policy to execute the lambda"
        )
        role = create_lambda_role()
        created = True
        # time.sleep(30) # wait for eventual consistency, we hope

    if "/" not in role:
        account = session.client("sts").get_caller_identity()["Account"]
        role = "arn:aws:iam::{}:role/{}".format(account, role)

    code_bytes = zip_bytes(code_file)

    client = session.client("lambda")

    print("Role={}".format(role))
    retries = 0
    while True:
        try:
            result = client.create_function(
                FunctionName=lambda_function_name,
                Runtime="python3.8",
                Role=role,
                Handler="lambda_function.lambda_handler",
                Code={"ZipFile": code_bytes},
                Description=lambda_description,
                Timeout=30,
                Publish=True,
            )
            return result
        except botocore.exceptions.ClientError as e:
            if (
                created
                and retries < 60
                and e.response["Error"]["Code"] == "InvalidParameterValueException"
            ):
                time.sleep(1)
            else:
                raise e


def create_lambda_role(name="run-notebook", session=None):
    """Create a default, minimal IAM role and policy for running the lambda function.

    Args:
        name (str): The name of the role and policy to create (default: "run-notebook").
        session (boto3.Session): The boto3 session to use. Will create a default session if not supplied (default: None).

    Returns:
        str: The ARN of the resulting role.
    """
    session = ensure_session(session)
    iam = session.client("iam")
    assume_role_policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    role = iam.create_role(
        RoleName=name,
        Description="A role for starting notebook execution from a lambda function",
        AssumeRolePolicyDocument=json.dumps(assume_role_policy_doc),
    )

    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["sagemaker:CreateProcessingJob", "iam:PassRole"],
                "Resource": "*",
            }
        ],
    }

    policy = iam.create_policy(
        PolicyName=name, PolicyDocument=json.dumps(policy_document)
    )

    iam.attach_role_policy(PolicyArn=policy["Policy"]["Arn"], RoleName=name)

    return role["Role"]["Arn"]


def zip_bytes(*files):
    file_dir = os.path.dirname(os.path.abspath(__file__))
    zip_io = io.BytesIO()
    with zip.ZipFile(zip_io, "w") as z:
        for cf in files:
            with open("{}/{}".format(file_dir, cf), "rb") as f:
                code_bytes = f.read()
            info = zip.ZipInfo(cf)
            info.external_attr = 0o777 << 16  # give full access to included file
            z.writestr(info, code_bytes)
    zip_io.seek(0)
    return zip_io.read()


class InvokeException(Exception):
    pass


def invoke(
    notebook,
    image="notebook-runner",
    input_path=None,
    output_prefix=None,
    parameters={},
    role=None,
    instance_type="ml.m5.large",
    extra_fns=[],
    session=None,
):
    """Run a notebook in SageMaker Processing producing a new output notebook.

    Invokes the installed Lambda function to immediately start a notebook execution in a SageMaker Processing Job.
    Can upload a local notebook file to run or use one previously uploaded to S3. This function returns when
    the Lambda function does without waiting for the notebook execution. To wait for the job and download the
    results, see :meth:`wait_for_complete` and :meth:`download_notebook`.

    To add extra arguments to the SageMaker Processing job, you can use the `extra_fns` argument. Each element of
    that list is a function that takes a dict and returns a dict with new fields added. For example::

        def time_limit(seconds):
            def proc(extras):
                extras["StoppingCondition"] = dict(MaxRuntimeInSeconds=seconds)
                return extras
            return proc

        job = run.invoke(notebook="powers.ipynb", extra_fns=[time_limit(86400)])

    Args:
        notebook (str): The notebook name. If `input_path` is None, this is a file to be uploaded before the Lambda is called.
                        all cases it is used as the name of the notebook when it's running and serves as the base of the
                        output file name (with a timestamp attached) (required).
        image (str): The ECR image that defines the environment to run the job (Default: "notebook-runner").
        input_path (str): The S3 object containing the notebook. If this is None, the `notebook` argument is
                          taken as a local file to upload (default: None).
        output_prefix (str): The prefix path in S3 for where to store the output notebook
                             (default: determined based on SageMaker Python SDK).
        parameters (dict): The dictionary of parameters to pass to the notebook (default: {}).
        role (str): The name of a role to use to run the notebook. This can be a name local to the account or a full ARN
                    (default: calls get_execution_role() or uses "BasicExecuteNotebookRole-<region>" if there's no execution role).
        instance_type (str): The SageMaker instance to use for executing the job (default: ml.m5.large).
        extra_fns (list of functions): The list of functions to amend the extra arguments for the processing job.
        session (boto3.Session): The boto3 session to use. Will create a default session if not supplied (default: None).

    Returns:
        The name of the processing job created to run the notebook.
    """
    session = ensure_session(session)

    if "/" not in image:
        account = session.client("sts").get_caller_identity()["Account"]
        region = session.region_name
        image = "{}.dkr.ecr.{}.amazonaws.com/{}:latest".format(account, region, image)

    if not role:
        try:
            role = get_execution_role(session)
        except ValueError:
            role = "BasicExecuteNotebookRole-{}".format(session.region_name)

    if "/" not in role:
        account = session.client("sts").get_caller_identity()["Account"]
        role = "arn:aws:iam::{}:role/{}".format(account, role)

    if input_path is None:
        input_path = upload_notebook(notebook)
    if output_prefix is None:
        output_prefix = get_output_prefix()

    extra_args = {}
    for f in extra_fns:
        extra_args = f(extra_args)

    args = {
        "image": image,
        "input_path": input_path,
        "output_prefix": output_prefix,
        "notebook": os.path.basename(notebook),
        "parameters": parameters,
        "role": role,
        "instance_type": instance_type,
        "extra_args": extra_args,
    }

    client = session.client("lambda")

    result = client.invoke(
        FunctionName=lambda_function_name,
        InvocationType="RequestResponse",
        LogType="None",
        Payload=json.dumps(args).encode("utf-8"),
    )
    payload = json.loads(result["Payload"].read())
    if "errorMessage" in payload:
        raise InvokeException(payload["errorMessage"])

    job = payload["job_name"]
    return job


RULE_PREFIX = "RunNotebook-"


def schedule(
    notebook,
    rule_name,
    schedule=None,
    event_pattern=None,
    image="notebook-runner",
    input_path=None,
    output_prefix=None,
    parameters={},
    role=None,
    instance_type="ml.m5.large",
    extra_fns=[],
    session=None,
):
    """Create a schedule for running a notebook in SageMaker Processing.

    Creates a CloudWatch Event rule to invoke the installed Lambda either on the provided schedule or in response
    to the provided event. \
  
    :meth:`schedule` can upload a local notebook file to run or use one previously uploaded to S3. 
    To find jobs run by the schedule, see :meth:`list_runs` using the `rule` argument to filter to 
    a specific rule. To download the results, see :meth:`download_notebook` (or :meth:`download_all` 
    to download a group of notebooks based on a :meth:`list_runs` call).

    To add extra arguments to the SageMaker Processing job, you can use the `extra_fns` argument. Each element of 
    that list is a function that takes a dict and returns a dict with new fields added. For example::

        def time_limit(seconds):
            def proc(extras):
                extras["StoppingCondition"] = dict(MaxRuntimeInSeconds=seconds)
                return extras
            return proc

        job = run.schedule(notebook="powers.ipynb", rule_name="Powers", schedule="rate(1 hour)", extra_fns=[time_limit(86400)])

    Args:
        notebook (str): The notebook name. If `input_path` is None, this is a file to be uploaded before the Lambda is called.
                        all cases it is used as the name of the notebook when it's running and serves as the base of the 
                        output file name (with a timestamp attached) (required).
        rule_name (str): The name of the rule for CloudWatch Events (required).
        schedule (str): A schedule string which defines when the job should be run. For details, 
                        see https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html 
                        (default: None. Note: one of `schedule` or `event_pattern` must be specified).
        event_pattern (str): A pattern for events that will trigger notebook execution. For details, 
                             see https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/CloudWatchEventsandEventPatterns.html. 
                             (default: None. Note: one of `schedule` or `event_pattern` must be specified).
        image (str): The ECR image that defines the environment to run the job (Default: "notebook-runner").
        input_path (str): The S3 object containing the notebook. If this is None, the `notebook` argument is
                          taken as a local file to upload (default: None).
        output_prefix (str): The prefix path in S3 for where to store the output notebook 
                             (default: determined based on SageMaker Python SDK).
        parameters (dict): The dictionary of parameters to pass to the notebook (default: {}).
        role (str): The name of a role to use to run the notebook. This can be a name local to the account or a full ARN
                    (default: calls get_execution_role() or uses "BasicExecuteNotebookRole-<region>" if there's no execution role).
        instance_type (str): The SageMaker instance to use for executing the job (default: ml.m5.large).
        extra_fns (list of functions): The list of functions to amend the extra arguments for the processing job.
        session (boto3.Session): The boto3 session to use. Will create a default session if not supplied (default: None).
    """
    kwargs = {}
    if schedule != None:
        kwargs["ScheduleExpression"] = schedule
    if event_pattern != None:
        kwargs["EventPattern"] = event_pattern
    if len(kwargs) == 0:
        raise Exception("Must specify one of schedule or event_pattern")

    session = ensure_session(session)

    # prepend a common prefix to the rule so it's easy to find notebook rules
    prefixed_rule_name = RULE_PREFIX + rule_name

    if "/" not in image:
        account = session.client("sts").get_caller_identity()["Account"]
        region = session.region_name
        image = "{}.dkr.ecr.{}.amazonaws.com/{}:latest".format(account, region, image)

    if not role:
        try:
            role = get_execution_role(session)
        except ValueError:
            role = "BasicExecuteNotebookRole-{}".format(session.region_name)

    if "/" not in role:
        account = session.client("sts").get_caller_identity()["Account"]
        role = "arn:aws:iam::{}:role/{}".format(account, role)

    if input_path is None:
        input_path = upload_notebook(notebook)
    if output_prefix is None:
        output_prefix = get_output_prefix()

    extra_args = {}
    for f in extra_fns:
        extra_args = f(extra_args)

    args = {
        "image": image,
        "input_path": input_path,
        "output_prefix": output_prefix,
        "notebook": os.path.basename(notebook),
        "parameters": parameters,
        "role": role,
        "instance_type": instance_type,
        "extra_args": extra_args,
        "rule_name": rule_name,
    }

    events = boto3.client("events")

    result = events.put_rule(
        Name=prefixed_rule_name,
        Description='Rule to run the Jupyter notebook "{}"'.format(notebook),
        **kwargs,
    )

    rule_arn = result["RuleArn"]

    lambda_ = session.client("lambda")
    lambda_.add_permission(
        StatementId="EB-{}".format(rule_name),
        Action="lambda:InvokeFunction",
        FunctionName="RunNotebook",
        Principal="events.amazonaws.com",
        SourceArn=rule_arn,
    )

    account = session.client("sts").get_caller_identity()["Account"]
    region = session.region_name
    target_arn = "arn:aws:lambda:{}:{}:function:{}".format(
        region, account, lambda_function_name
    )

    result = events.put_targets(
        Rule=prefixed_rule_name,
        Targets=[{"Id": "Default", "Arn": target_arn, "Input": json.dumps(args)}],
    )


def unschedule(rule_name, session=None):
    """Delete an existing notebook schedule rule.

    Args:
        rule_name (str): The name of the rule for CloudWatch Events (required).
        session (boto3.Session): The boto3 session to use. Will create a default session if not supplied (default: None).
    """
    prefixed_rule_name = RULE_PREFIX + rule_name

    session = ensure_session(session)
    events = boto3.client("events")
    lambda_ = session.client("lambda")

    try:
        lambda_.remove_permission(
            FunctionName="RunNotebook", StatementId="EB-{}".format(rule_name)
        )
    except botocore.exceptions.ClientError as ce:
        message = ce.response.get("Error", {}).get("Message", "Unknown error")
        if (
            not "is not found" in message
        ):  # ignore it if the permission was already deleted
            raise

    events.remove_targets(Rule=prefixed_rule_name, Ids=["Default"])

    events.delete_rule(Name=prefixed_rule_name)


def describe_schedules(n=0, rule_prefix=None, session=None):
    """A generator that returns descriptions of all the notebook schedule rules

    Args:
       n (int): The number of rules to return or all runs if 0 (default: 0)
       rule_prefix (str): If not None, return only rules whose names begin with the prefix (default: None)
       session (boto3.Session): The boto3 session to use. Will create a default session if not supplied (default: None)."""

    if not rule_prefix:
        rule_prefix = ""
    rule_prefix = RULE_PREFIX + rule_prefix

    session = ensure_session(session)
    client = session.client("events")
    paginator = client.get_paginator("list_rules")
    page_iterator = paginator.paginate(NamePrefix=rule_prefix)

    for page in page_iterator:
        for item in page["Rules"]:
            rule_name = item["Name"][len(RULE_PREFIX) :]
            d = describe_schedule(rule_name, item, session)
            yield d

            if n > 0:
                n = n - 1
                if n == 0:
                    return


def describe_schedule(rule_name, rule_item=None, session=None):
    """Describe a notebook execution schedule.

    Args:
     rule_name (str): The name of the schedule rule to describe. (Required)
     rule_item: Only used to optimize :meth:`describe_schedules`. Should be omitted in normal use. (Default: None)

    Returns:
      A dictionary with keys for each element of the rule. For example::

        {'name': 'Powers',
        'notebook': 'powers.ipynb',
        'parameters': {},
        'schedule': 'rate(1 hour)',
        'event_pattern': None,
        'image': 'notebook-runner',
        'instance': 'ml.m5.large',
        'role': 'BasicExecuteNotebookRole-us-west-2',
        'state': 'ENABLED',
        'input_path': 's3://sagemaker-us-west-2-123456789012/papermill_input/notebook-2020-11-02-19-49-24.ipynb',
        'output_prefix': 's3://sagemaker-us-west-2-123456789012/papermill_output'}
    """
    rule_name = RULE_PREFIX + rule_name
    session = ensure_session(session)
    ev = session.client("events")

    if not rule_item:
        rule_item = ev.describe_rule(Name=rule_name)

    targets = ev.list_targets_by_rule(Rule=rule_name)
    if "Targets" in targets and len(targets["Targets"]) > 0:
        target = targets["Targets"][0]
        inp = json.loads(target["Input"])
    else:
        # This is a broken rule. This could happen if we have weird IAM permissions and try to do a delete.
        inp = {}

    d = dict(
        name=rule_name[len(RULE_PREFIX) :],
        notebook=inp.get("notebook", ""),
        parameters=inp.get("parameters", ""),
        schedule=rule_item.get("ScheduleExpression"),
        event_pattern=rule_item.get("EventPattern"),
        image=abbreviate_image(inp.get("image", "")),
        instance=inp.get("instance_type", ""),
        role=abbreviate_role(inp.get("role", "")),
        state=rule_item["State"],
        input_path=inp.get("input_path", ""),
        output_prefix=inp.get("output_prefix", ""),
    )

    return d


image_pat = re.compile(r"([0-9]+)\.[^/]+/(.*)$")


def base_image(s):
    """Determine just the repo and tag from the ECR image descriptor"""
    m = image_pat.match(s)
    if m:
        return m.group(2)
    else:
        return s


role_pat = re.compile(r"arn:aws:iam::([0-9]+):role/(.*)$")


def base_role(s):
    """Determine just the role name from a role arn"""
    m = role_pat.match(s)
    if m:
        return m.group(2)
    else:
        return s


def list_schedules(n=0, rule_prefix=None, session=None):
    """Return a pandas data frame of the schedule rules.

    Args:
        n (int): The number of rules to return or all rules if 0 (default: 0)
        rule_prefix (str): If not None, return only rules whose names begin with the prefix (default: None)
        session (boto3.Session): The boto3 session to use. Will create a default session if not supplied (default: None).
    """
    import pandas as pd  # pylint: disable=import-error

    l = pd.DataFrame(describe_schedules(n=n, rule_prefix=rule_prefix, session=session))
    if l is not None and l.shape[0] > 0:
        l = l.drop(columns=["input_path", "output_prefix"])
        l["image"] = l["image"].map(base_image)
        l["role"] = l["role"].map(base_role)
        for c in ["schedule", "event_pattern"]:
            l[c] = l[c].map(lambda x: x if x else "")

    return l
