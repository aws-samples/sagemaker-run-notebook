import json
import os
import re
import time

import boto3


def execute_notebook(
    *,
    image,
    input_path,
    output_prefix,
    notebook,
    parameters,
    role,
    instance_type,
    rule_name,
    extra_args,
):
    session = ensure_session()
    region = session.region_name

    account = session.client("sts").get_caller_identity()["Account"]
    if not image:
        image = "notebook-runner"
    if "/" not in image:
        image = f"{account}.dkr.ecr.{region}.amazonaws.com/{image}"
    if ":" not in image:
        image = image + ":latest"

    if not role:
        role = f"BasicExecuteNotebookRole-{region}"
    if "/" not in role:
        role = f"arn:aws:iam::{account}:role/{role}"

    if output_prefix is None:
        output_prefix = os.path.dirname(input_path)

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

    if extra_args is not None:
        api_args = merge_extra(api_args, extra_args)

    api_args["Environment"]["PAPERMILL_INPUT"] = local_input
    api_args["Environment"]["PAPERMILL_OUTPUT"] = local_output + result
    if os.environ.get("AWS_DEFAULT_REGION") != None:
        api_args["Environment"]["AWS_DEFAULT_REGION"] = os.environ["AWS_DEFAULT_REGION"]
    api_args["Environment"]["PAPERMILL_PARAMS"] = json.dumps(parameters)
    api_args["Environment"]["PAPERMILL_NOTEBOOK_NAME"] = base
    if rule_name is not None:
        api_args["Environment"]["AWS_EVENTBRIDGE_RULE"] = rule_name

    client = boto3.client("sagemaker")
    result = client.create_processing_job(**api_args)
    job_arn = result["ProcessingJobArn"]
    job = re.sub("^.*/", "", job_arn)
    return job


def merge_extra(orig, extra):
    result = dict(orig)
    result["ProcessingInputs"].extend(extra.get("ProcessingInputs", []))
    result["ProcessingOutputConfig"]["Outputs"].extend(
        extra.get("ProcessingOutputConfig", {}).get("Outputs", [])
    )
    if "KmsKeyId" in extra.get("ProcessingOutputConfig", {}):
        result["ProcessingOutputConfig"]["KmsKeyId"] = extra["ProcessingOutputConfig"][
            "KmsKeyId"
        ]
    result["ProcessingResources"]["ClusterConfig"] = {
        **result["ProcessingResources"]["ClusterConfig"],
        **extra.get("ProcessingResources", {}).get("ClusterConfig", {}),
    }
    result = {
        **result,
        **{
            k: v
            for k, v in extra.items()
            if k in ["ExperimentConfig", "NetworkConfig", "StoppingCondition", "Tags"]
        },
        "Environment": {**orig.get("Environment", {}), **extra.get("Environment", {})},
    }
    return result


def ensure_session(session=None):
    """If session is None, create a default session and return it. Otherwise return the session passed in"""
    if session is None:
        session = boto3.session.Session()
    return session


def lambda_handler(event, context):
    job = execute_notebook(
        image=event.get("image"),
        input_path=event["input_path"],
        output_prefix=event.get("output_prefix"),
        notebook=event.get("notebook"),
        parameters=event.get("parameters", dict()),
        role=event.get("role"),
        instance_type=event.get("instance_type", "ml.m5.large"),
        rule_name=event.get("rule_name"),
        extra_args=event.get("extra_args"),
    )
    return {"job_name": job}
