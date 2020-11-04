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
import json
import os
import subprocess
import textwrap
import time

import boto3

import sagemaker_run_notebook as run
import sagemaker_run_notebook.create_infrastructure as infra
import sagemaker_run_notebook.container_build as container_build
import sagemaker_run_notebook.emr as emr


def xform_param(arg):
    "Take an arg string of the form x=5 and turn it into a tuple (x,5) with the second part converted to a number, if possible"
    s = arg.split("=")
    if len(s) != 2:
        raise ValueError(f'Parameter "{arg}" is not in the form "paramter=value"')
    k = s[0]
    try:
        v = json.loads(s[1])
    except json.JSONDecodeError:
        v = s[1]
    return (k, v)


def process_params(params):
    if not params:
        return []
    else:
        return {k: v for k, v in [xform_param(p[0]) for p in params]}


def load_extra(extra):
    if extra is None:
        return None
    elif extra.startswith("@"):
        with open(extra[1:], mode="r") as f:
            return json.load(f)
    else:
        return json.loads(extra)


def base_extras(extras):
    def proc(extra):
        if extra:
            raise "Base extras must be first"
        return extras

    return proc


def run_notebook(args):
    params = process_params(args.p)
    if args.notebook.startswith("s3://"):
        input_path = args.notebook
        notebook = os.path.basename(args.notebook)
    else:
        input_path = None
        notebook = args.notebook
    extra_fns = []
    if args.extra:
        extra_fns.append(base_extras(load_extra(args.extra)))
    if args.emr:
        extra_fns.append(emr.add_emr_cluster(args.emr))
    try:
        job_name = run.invoke(
            image=args.image,
            input_path=input_path,
            output_prefix=args.output_prefix,
            notebook=notebook,
            parameters=params,
            role=args.role,
            instance_type=args.instance,
            extra_fns=extra_fns,
        )
    except run.InvokeException as ie:
        print(f"Error starting run: {str(ie)}")
        return
    except FileNotFoundError as fe:
        print(str(fe))
        return
    print(f"Started processing job {job_name}")
    if args.no_wait:
        return
    status, failure = run.wait_for_complete(job_name)
    print(f"Run finished with status {status}")
    if failure:
        print(failure)
    else:
        run.download_notebook(job_name, args.output_dir)


def local_notebook(args):
    params = process_params(args.p)
    notebook_dir = os.path.dirname(args.notebook)
    notebook = os.path.basename(args.notebook)

    nb_name, nb_ext = os.path.splitext(notebook)
    timestamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
    result = "{}-{}{}".format(nb_name, timestamp, nb_ext)

    session = boto3.session.Session()
    region = session.region_name
    account = session.client("sts").get_caller_identity()["Account"]
    image = args.image
    if not image:
        image = "notebook-runner"
    if "/" not in image:
        image = f"{account}.dkr.ecr.{region}.amazonaws.com/{image}"
    if ":" not in image:
        image = image + ":latest"

    base_cmd = ["docker", "run", "--rm", "-td" if args.no_wait else "-ti"]
    mnts = [
        "-v",
        os.path.abspath(notebook_dir) + ":/opt/ml/processing/input",
        "-v",
        os.path.abspath(args.output_dir) + ":/opt/ml/processing/output",
    ]
    env = [
        "-e",
        f"PAPERMILL_INPUT=/opt/ml/processing/input/{notebook}",
        "-e",
        f"PAPERMILL_OUTPUT=/opt/ml/processing/output/{result}",
        "-e",
        f"PAPERMILL_PARAMS={json.dumps(params)}",
        "-e",
        f"PAPERMILL_NOTEBOOK_NAME={notebook}",
        "-e",
        f"AWS_DEFAULT_REGION={region}",
    ]
    cmd = [*base_cmd, *mnts, *env, image, "run_notebook"]
    p = subprocess.run(cmd)
    print(f"Run finished with status {p.returncode}")


def download_notebook(args):
    if args.wait:
        status, failure = run.wait_for_complete(args.run_name)
        if status != "Completed":
            print(f"Run finished with status {status}")
            if failure:
                print(failure)
            return
    run.download_notebook(args.run_name, args.output_dir)


def stop_run(args):
    run.stop_run(args.run_name)


def build_output_params(desc):
    if desc and desc != "[]":
        params = [f"{k}={v}" for k, v in json.loads(desc).items()]
        if len(params) == 0:
            params = [""]
    else:
        params = [""]
    return params


def list_runs(args):
    runs = run.describe_runs(n=args.max, notebook=args.notebook, rule=args.rule)
    print(
        "Date                 Rule                 Notebook              Parameters           Status     Job"
    )
    for r in runs:
        params = build_output_params(r["Parameters"])
        print(
            f"{r['Created']:%Y-%m-%d %H:%M:%S}  {r['Rule'][:20]:20} {r['Notebook'][:20]:20}  {params[0][:20]:20} {r['Status']:10} {r['Job']}  "
        )
        failure = textwrap.wrap(r["Failure"], 60) if r["Status"] == "Failed" else []
        offset = 1
        for l in failure:
            if len(params) > offset:
                p = params[offset]
            else:
                p = ""
            print(f"{'':64}{p[:20]:20} {l}")
            offset += 1

        for p in params[offset:]:
            print(f"{'':64}{p[:20]:20}")


def schedule(args):
    params = process_params(args.p)
    if args.notebook.startswith("s3://"):
        input_path = args.notebook
        notebook = os.path.basename(args.notebook)
    else:
        input_path = None
        notebook = args.notebook

    extra_fns = []
    if args.extra:
        extra_fns.append(base_extras(load_extra(args.extra)))
    if args.emr:
        extra_fns.append(emr.add_emr_cluster(args.emr))

    run.schedule(
        rule_name=args.name,
        schedule=args.at,
        event_pattern=args.event,
        image=args.image,
        input_path=input_path,
        output_prefix=args.output_prefix,
        notebook=notebook,
        parameters=params,
        role=args.role,
        instance_type=args.instance,
        extra_fns=extra_fns,
    )


def unschedule(args):
    run.unschedule(rule_name=args.rule_name)


def list_rules(args):
    rules = run.describe_schedules(n=args.max, rule_prefix=args.prefix)
    print(
        "Name                  Notebook             Parameters           Schedule              Event Pattern"
    )
    for r in rules:
        if args.notebook and r["notebook"] != args.notebook:
            continue
        if r["parameters"] == None or r["parameters"] == []:
            params = [""]
        else:
            params = params = [f"{k}={v}" for k, v in r["parameters"].items()]
            if len(params) == 0:
                params = [""]
        schedule = r["schedule"] if r["schedule"] else ""
        event_pattern = r["event_pattern"] if r["event_pattern"] else ""
        print(
            f"{r['name'][:20]:20}  {r['notebook'][:20]:20} {params[0][:20]:20} {schedule[:20]:20}  {event_pattern[:20]:20}"
        )
        for p in params[1:]:
            print(f"{'':43}{p[:20]:20}")


def create_infrastructure(args):
    infra.create_infrastructure(update=args.update)


def create_container(args):
    container_build.create_container(
        args.repository,
        args.role,
        args.bucket,
        args.base,
        args.requirements,
        args.script,
        args.kernel,
        log=not args.no_logs,
    )


def cli_argparser():
    region = boto3.session.Session().region_name
    default_execution_role = f"BasicExecuteNotebookRole-{region}"
    container_build_role = f"ExecuteNotebookCodeBuildRole-{region}"

    parser = argparse.ArgumentParser(
        description="A command line interface for running and scheduling notebooks in SageMaker"
    )
    parser.add_argument(
        "-v", "--version", action="store_true", help="Display current version and exit"
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    run_parser = subparsers.add_parser("run", help="Run a notebook now")
    run_parser.add_argument(
        "notebook", help="The name of the notebook to run (local file or an s3 URL)"
    )
    run_parser.add_argument(
        "-p",
        action="append",
        nargs=1,
        help="Specify a parameter like -p x=7. Can be repeated.",
    )
    run_parser.add_argument(
        "--output-prefix",
        help="Where in S3 to put the output (default: SageMaker Python SDK bucket)",
    )
    run_parser.add_argument(
        "--role",
        help=f"The IAM role to use when running the notebook (default: {default_execution_role})",
        default=default_execution_role,
    )
    run_parser.add_argument(
        "--instance",
        help="The EC2 instance type to use to run the notebook (default: ml.m5.large)",
        default="ml.m5.large",
    )
    run_parser.add_argument(
        "--image",
        help="The Docker image in ECR to use to run the notebook (default: notebook-runner)",
        default="notebook-runner",
    )
    run_parser.add_argument(
        "--extra",
        help="Extra arguments to pass to SageMaker processing formatted as JSON (use @filename to read JSON from a file) (default: None)",
    )
    run_parser.add_argument(
        "--emr",
        help="The name of an EMR cluster to connect to for SparkMagic (default: None)",
    )
    run_parser.add_argument(
        "--output-dir",
        help="The directory to download the notebook to (default: .)",
        default=".",
    )
    run_parser.add_argument(
        "--no-wait",
        help="Launch the notebook run but don't wait for it to complete",
        action="store_true",
    )
    run_parser.set_defaults(func=run_notebook)

    download_parser = subparsers.add_parser(
        "download", help="Download the output of a notebook execution"
    )
    download_parser.add_argument(
        "run_name", metavar="run-name", help="The name of the notebook execution run"
    )
    download_parser.add_argument(
        "--output-dir",
        help="The directory to download the notebook to (default: .)",
        default=".",
    )
    download_parser.add_argument(
        "--wait",
        help="Wait for the job to complete before downloading",
        action="store_true",
    )
    download_parser.set_defaults(func=download_notebook)

    stoprun_parser = subparsers.add_parser(
        "stop-run",
        help="Stop the specified notebook execution run without waiting for it to complete",
    )
    stoprun_parser.add_argument(
        "run_name", metavar="run-name", help="The name of the notebook execution run"
    )
    stoprun_parser.set_defaults(func=stop_run)

    listrun_parser = subparsers.add_parser("list-runs", help="List notebook runs")
    listrun_parser.add_argument(
        "--rule", help="List only runs started by the specified schedule rule"
    )
    listrun_parser.add_argument(
        "--notebook", help="List only runs of the specified notebook"
    )
    listrun_parser.add_argument(
        "--max", help="Maximum number of runs to show", type=int, default=9999999
    )
    listrun_parser.set_defaults(func=list_runs)

    schedule_parser = subparsers.add_parser(
        "schedule",
        help="Create a rule to run a notebook on a schedule or in response to an event",
    )
    schedule_parser.add_argument(
        "notebook", help="The name of the notebook to run (local file or an s3 URL)"
    )
    schedule_parser.add_argument(
        "--name", help="The name of the rule to create.", required=True
    )
    schedule_parser.add_argument(
        "-p",
        action="append",
        nargs=1,
        help="Specify a parameter like -p x=7. Can be repeated.",
    )
    schedule_parser.add_argument(
        "--output-prefix",
        help="Where in S3 to put the output (default: SageMaker Python SDK bucket)",
    )
    schedule_parser.add_argument(
        "--role",
        help=f"The IAM role to use when running the notebook (default: {default_execution_role})",
        default=default_execution_role,
    )
    schedule_parser.add_argument(
        "--instance",
        help="The EC2 instance type to use to run the notebook (default: ml.m5.large)",
        default="ml.m5.large",
    )
    schedule_parser.add_argument(
        "--image",
        help="The Docker image in ECR to use to run the notebook (default: notebook-runner)",
        default="notebook-runner",
    )
    schedule_parser.add_argument(
        "--emr",
        help="The name of an EMR cluster to connect to for SparkMagic (default: None)",
    )
    schedule_parser.add_argument(
        "--extra",
        help="Extra arguments to pass to SageMaker processing formatted as JSON (use @filename to read JSON from a file) (default: None)",
    )
    schedule_parser.add_argument(
        "--at",
        help="When to run the notebook (see https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html for syntax)",
    )
    schedule_parser.add_argument(
        "--event", help="Event that will trigger the notebook run"
    )
    schedule_parser.set_defaults(func=schedule)

    unschedule_parser = subparsers.add_parser(
        "unschedule", help="Delete the specified schedule rule"
    )
    unschedule_parser.add_argument(
        "rule_name", metavar="rule-name", help="The name of the rule to delete"
    )
    unschedule_parser.set_defaults(func=unschedule)

    listrules_parser = subparsers.add_parser("list-rules", help="List schedule rules")
    listrules_parser.add_argument(
        "--prefix", help="List only rules where the rule name has the specified prefix"
    )
    listrules_parser.add_argument(
        "--notebook", help="List only rules with the specified notebook"
    )
    listrules_parser.add_argument(
        "--max", help="Maximum number of rules to show", type=int, default=9999999
    )
    listrules_parser.set_defaults(func=list_rules)

    local_parser = subparsers.add_parser(
        "local", help="Run a notebook locally using Docker"
    )
    local_parser.add_argument("notebook", help="The name of the notebook file to run")
    local_parser.add_argument(
        "-p",
        action="append",
        nargs=1,
        help="Specify a parameter like -p x=7. Can be repeated.",
    )
    local_parser.add_argument(
        "--image",
        help="The Docker image in ECR to use to run the notebook (default: notebook-runner)",
        default="notebook-runner",
    )
    local_parser.add_argument(
        "--output-dir",
        help="The directory to output the notebook to (default: .)",
        default=".",
    )
    local_parser.add_argument(
        "--no-wait",
        help="Launch the notebook run but don't wait for it to complete",
        action="store_true",
    )
    local_parser.set_defaults(func=local_notebook)

    createinfra_parser = subparsers.add_parser(
        "create-infrastructure",
        help="Use CloudFormation to set up the required Lambda function and IAM roles and policies",
    )
    createinfra_parser.add_argument(
        "--update",
        help="Add this flag to update an existing stack",
        action="store_true",
    )
    createinfra_parser.set_defaults(func=create_infrastructure)

    container_parser = subparsers.add_parser(
        "create-container",
        help="Use CodeBuild to build a Docker image for notebook execution",
    )
    container_parser.add_argument(
        "repository",
        help="The ECR repository for the image (default: notebook-runner)",
        nargs="?",
        default="notebook-runner",
    )
    container_parser.add_argument(
        "--base",
        help=f"The Docker image to base the new image on (default: {container_build.default_base})",
        default=container_build.default_base,
    )
    container_parser.add_argument(
        "--requirements",
        help="A requirements.txt file to define custom dependencies for the container",
    )
    container_parser.add_argument(
        "--script",
        help="A shell script to run while building the container (after any requirements are installed)",
    )
    container_parser.add_argument(
        "-k",
        "--kernel",
        help="The name of the kernel to use to run the notebook (default: first Python kernel)",
    )
    container_parser.add_argument(
        "--role",
        help=f"The IAM role for CodeBuild to use (default: {container_build_role}).",
        default=container_build_role,
    )
    container_parser.add_argument(
        "--bucket",
        help="The S3 bucket to use for sending data to CodeBuild (if None, use the SageMaker SDK default bucket).",
    )
    container_parser.add_argument(
        "--no-logs",
        action="store_true",
        help="Don't show the logs of the running CodeBuild build",
    )

    container_parser.set_defaults(func=create_container)

    return parser


def main():
    parser = cli_argparser()
    args = parser.parse_args()
    if args.version:
        print("v{}".format(run.__version__))
    elif args.subcommand is None:
        parser.print_help()
    else:
        args.func(args)


if __name__ == "__main__":
    main()
