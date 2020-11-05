# Build Your Own Notebook Execution Environment

## Overview

In this tutorial, we show you how to use AWS tools directly to execute and schedule notebooks. To make the process easier, we have provided a CloudFormation template to set up the Lambda function you'll need and some IAM roles and policies that you'll use when running notebooks. We've also provided scripts for building and customizing the Docker container images that SageMaker Processing Jobs will use when running the notebooks.

While the library, command-line interface, and GUI options provide more convenience, there are several reasons why you may prefer to build your own infrastructure and use it to execute and schedule notebooks:

1. You want to integrate notebook execution into an existing system that already sets up much of the environment.
2. You want to customize the system in ways not supported by the other tools.
3. You have specific security requirements that mean you want to customize/restrict permissions built into the CloudFormation template.
4. You want to invoke these services from a language other than Python.
5. Any other reason you want.

Note that there isn't an either/or choice. You can customize your infrastructure or containers with the resources provided here and then use the `sagemaker-run-notebook` library to run notebooks on that infrastructure. Or you can create your infrastructure with `run-notebook create-infrastructure` and then use the methods shown below to execute notebooks from Java code.

## Prerequisites

What you'll need:

1. AWS client code installed. This can be the [AWS CLI][aws-cli] or [AWS language bindings][aws-tools] for your language.
2. To have AWS credentials set up that give you full permission on SageMaker, IAM, CloudFormation, Lambda, Cloudwatch Events, and ECR.
3. Docker installed locally.
4. Two files from the [release on GitHub][release]: cloudformation.yml and container.tar.gz.

> _Note:_ This tutorial shows all these operations using the AWS CLI, but the equivalent operations using the Boto3 library in Python or language bindings in other languages will work just as well.

[aws-cli]: https://aws.amazon.com/cli/
[aws-tools]: https://aws.amazon.com/tools/
[release]: https://github.com/aws-samples/sagemaker-run-notebook/releases/latest

## Instructions

#### 1. Run CloudFormation template to set up roles, policies, and the Lambda function

```sh
$ aws cloudformation create-stack --stack-name sagemaker-run-notebook --template-body file://$(pwd)/cloudformation.yml --capabilities CAPABILITY_NAMED_IAM
```

To see if the stack was successfully created, you can use the command:

```sh
$ aws cloudformation describe-stacks --stack-name sagemaker-run-notebook
```

And the `StackStatus` in the command should be `CREATE_COMPLETE`.

One of the policies created here is `ExecuteNotebookClientPolicy-us-east-1` (replace `us-east-1` with the name of the region you're running in). If you're not running with administrative permissions, you should add that policy to the user or role that you're using to invoke and schedule notebooks. For complete information on the roles and policies as well as the source code for the Lambda function, see the `cloudformation.yml` file which you can view [on GitHub][cfn-template] or download from the [latest release][release].

[cfn-template]: https://github.com/aws-samples/sagemaker-run-notebook/blob/master/sagemaker_run_notebook/cloudformation-base.yml

#### 2. Create a container image to run your notebook

Jobs run in SageMaker Processing Jobs run inside a Docker container. For this project, we have defined
the container to include a script to set up the environment and run Papermill on the
input notebook.

The `container.tar.gz` file in the [latest release][release] contains everything you need to build and customize the container. You can edit the `requirements.txt` file to specify Python libraries that your notebooks will need as described [in the pip documentation][requirements].

```sh
$ tar xvf container.tar.gz
$ cd container
<edit requirements.txt to add any dependencies you need>
$ ./build-and-push.sh notebook-runner
```

> _Note:_ You must have Docker installed for `build-and-push.sh` to work. If you prefer not to install and run Docker, use the convenience package as described in [Create a Docker container to run the notebook](#3-create-a-docker-container-to-run-the-notebook). That technique uses CodeBuild to build the container image to use.

#### 3. Copy your notebook to S3

```
$ aws s3 cp mynotebook.ipynb s3://mybucket/
```

(replace "mynotebook" and "mybucket" with appropriate values)

#### 4. Run a notebook on demand

```sh
$ aws lambda invoke --function-name RunNotebook --payload '{"input_path": "s3://mybucket/mynotebook.ipynb", "parameters": {"p": 0.75}}' result.json
```
  
The file `result.json` will have your SageMaker Processing job name.

Now the job is running and it will take a few minutes to provision a node for processing and run.

The Lambda function provided has many options for how your notebook is run (like customizing the container image, using a specific IAM role, etc.). You can see all of these in the Lambda function definition included in the CloudFormation template.

You should feel free to customize the way the Lambda function calls SageMaker Processing to add any custom behavior that you would like to have.

#### 5. View the job

Extract the job name from the result.json and run the following command to view the job status:

```sh
$ aws sagemaker describe-processing-job  --processing-job-name myjob --output json
{
    ...
    "ProcessingOutputConfig": {
        "Outputs": [
            {
                ...
                "S3Output": {
                    "S3Uri": "s3://mybucket",
                    ...
                }
            }
        ]
    },
    ...
    "Environment": {
        ...
        "PAPERMILL_OUTPUT": "/opt/ml/processing/output/mynotebook-2020-06-08-03-44-04.ipynb",
        ...
    },
    ...
    "ProcessingJobStatus": "InProgress",
    ...
}
```

By viewing the status in the result, you can see whether the job is in progress, succeeded, or failed.

#### 6. Retrieve the output notebook

When the job succeeds, the output is saved back to S3. To find the S3 object name, combine the output path from the processing job with the base file name from the environment variable `PAPERMILL_OUTPUT`. For instance, in the above example the output notebook would be `s3://mybucket//mynotebook-2020-06-08-03-44-04.ipynb`.

You can then use the following command to copy the notebook to your local current directory:

```sh
$ aws s3 cp s3://outputpath/basename.ipynb .
```

#### 7. Schedule a notebook to run

You can use CloudWatch Events to schedule notebook executions. For example, to run the notebook that we previously uploaded every day at 1:15 use the following commands:

```sh
$ aws events put-rule --name "RunNotebook-test" --schedule "cron(15 1 * * ? *)"
$ aws lambda add-permission --statement-id EB-RunNotebook-test \
              --action lambda:InvokeFunction \
              --function-name RunNotebook \
              --principal events.amazonaws.com \
              --source-arn arn:aws:events:us-east-1:981276346578:rule/RunNotebook-test
$ aws events put-targets --rule RunNotebook-test \
      --targets '[{"Id": "Default", "Arn": "arn:aws:lambda:us-east-1:981276346578:function:RunNotebook", "Input": "{ \"input_path\": \"s3://mybucket/mynotebook.ipynb\", \"parameters\": {\"p\": 0.75}}"}]'
```

Substitute your account number in place of 981276346578 in the source ARN and the Lambda function ARN. Substitute the region name your working in for "us-east-1" in both ARNs.

Substitute the location where you stored your notebook as the `input` path argument.

The `Input` field in the `put-targets` call are the arguments to the Lambda function and they can be customized to anything the Lambda accepts. (See [`cloudformation.yml`][cfn-template] for the Lambda function definition.)

Note that times are always in UTC. To see the full rules on times, view the Cloudwatch Events documentation here: [Schedule Expressions for Rules][sched]

[sched]: https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html

When the notebook has run, you can find the jobs with `aws sagemaker list-processing-jobs` and then describe the job and download the notebook as described above.
