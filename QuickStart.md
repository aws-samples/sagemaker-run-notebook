# Quick Start

This document outlines how to execute and schedule notebooks in SageMaker using SageMaker Processing Jobs, AWS Lambda, and Cloudwatch Events.

Depending on your preference, we outline three ways to do this. All have the same functionality, but different interfaces. You can use them in combination if you choose.

First, we show you how to use AWS tools directly to execute and schedule notebooks. To make the process easier, we have provided a CloudFormation template to set up the Lambda function you'll need and some IAM roles and policies that you'll use when running notebooks. We've also provided scripts for building and customizing the Docker container images that SageMaker Processing Jobs will use when running the notebooks.

Second, we show you how to install and use the convenience package that wraps the AWS tools in a CLI and Python library that give you a more natural interface to running and scheduling notebooks.

Finally, for those who prefer an interactive experience, the convenience package includes a JupyterLab extension that can be enabled for JupyterLab running locally, in SageMaker Studio, or on a SageMaker notebook instance.

We use the open source tool [Papermill][papermill] to execute the notebooks. Papermill has many features, but one of the most interesting is that you can add parameters to your notebook runs. To do this, you set a tag on a single cell in your notebook that marks it as the "parameter cell". Papermill will insert a cell directly after that at runtime with the parameter values you set when starting the job. You can see details in the Papermill docs [here][papermill-parameters].

[papermill]: https://github.com/nteract/papermill
[papermill-parameters]: https://papermill.readthedocs.io/en/latest/usage-parameterize.html

You can go directly to the quick start you prefer:

* [Using existing AWS primitives](#using-existing-aws-primitives)
* [Using the CLI provided by the convenience package](#using-the-cli-provided-by-the-convenience-package)
* [Activating the JupyterLab extension](#activating-the-jupyterlab-extension)

## Using existing AWS primitives

You'll need to have AWS credentials set up that give you full permission on SageMaker, IAM, CloudFormation, Lambda, Cloudwatch Events, and ECR. You will also need to have Docker installed locally.

You'll need two files that were provided in the package you received: cloudformation.yml and container.tar.gz.

> _Note:_ This Quick Start shows all these operations using the AWS CLI, but the equivalent operations using the Boto3 library in Python or language bindings in other languages will work just as well.

#### 1. Run CloudFormation template to set up roles, policies, and the Lambda function

```sh
$ aws cloudformation create-stack --stack-name sagemaker-run-notebook --template-body file://$(pwd)/cloudformation.yml --capabilities CAPABILITY_NAMED_IAM
```

To see if the stack was successfully created, you can use the command:

```sh
$ aws cloudformation describe-stacks --stack-name sagemaker-run-notebook
```

And the `StackStatus` in the command should be `CREATE_COMPLETE`.

One of the policies created here is `ExecuteNotebookClientPolicy-us-east-1` (replace `us-east-1` with the name of the region you're running in). If you're not running with administrative permissions, you should add that policy to the user or role that you're using to invoke and schedule notebooks. For complete information on the roles and policies as well as the source code for the Lambda function, see the `cloudformation.yml` file distributed with the software.

#### 2. Create a container image to run your notebook

Jobs run in SageMaker Processing Jobs run inside a Docker container. For this project, we have defined
the container to include a script to set up the environment and run Papermill on the
input notebook.

The `container.tar.gz` file distributed with the release contains everything you need to build and customize the container. You can edit the `requirements.txt` file to specify Python libraries that your notebooks will need as described [here][requirements].

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

The `Input` field in the `put-targets` call are the arguments to the Lambda function and they can be customized to anything the Lambda accepts. (See `cloudformation.yml` for the Lambda function definition.)

Note that times are always in UTC. To see the full rules on times, view the Cloudwatch Events documentation here: [Schedule Expressions for Rules][sched]

[sched]: https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html

When the notebook has run, you can find the jobs with `aws sagemaker list-processing-jobs` and then describe the job and download the notebook as described above.

## Using the CLI provided by the convenience package

To follow this recipe, you'll need to have AWS credentials set up that give you full permission on CloudFormation. You'll add more permissions with the installed policy later in the recipe.

You'll need one file that was provided with this distribution: sagemaker_run_notebook-0.13.0.tar.gz.

#### 1. Install the library

```sh
$ pip install sagemaker_run_notebook-0.13.0.tar.gz
```

This installs the sagemaker run notebook library and CLI tool. It also installs the JupyterLab plug-in but does not activate it. See below in "Using the JupyterLab Extension" for more information.

To get information on how to use the CLI, run `run-notebook --help`.

The instructions here all use the CLI commands but you can also use the library from Python programs and Jupyter notebooks with a statement like `import sagemaker_run_notebook as run` and then `run.invoke(...)`, etc.

#### 2. Create roles, policies and the Lambda function

```sh
$ run-notebook create-infrastructure
```

One of the policies created here is `ExecuteNotebookClientPolicy-us-east-1` (replace `us-east-1` with the name of the region you're running in). If you're not running with administrative permissions, you should add that policy to the user or role that you're using to invoke and schedule notebooks. 

For complete information on the roles and policies as well as the source code for the Lambda function, see the `cloudformation.yml` file distributed with the software.

#### 3. Create a Docker container to run the notebook

Jobs run in SageMaker Processing Jobs run inside a Docker container. For this project, we have defined
the container to include a script to set up the environment and run Papermill on the
input notebook.

```sh
$ run-notebook create-container
```

This creates a temporary project in AWS CodeBuild to build your Docker container image so there's no need to install Docker locally.

_Optional_: If you want to add custom dependencies to your container, you can create a requirements.txt file as described at [Requirements Files][requirements] in the `pip` documentation. Then add that to your CLI command like this:

```sh
$ run-notebook create-container --requirements requirements.txt
```

If you'd rather do the Docker build on your local system, you can use the recipe specified in [Create a container image to run your notebook](#2-create-a-container-image-to-run-your-notebook)

[requirements]: https://pip.pypa.io/en/stable/user_guide/#requirements-files

#### 4. Run a notebook on demand

To run a notebook:

```sh
$ run-notebook run mynotebook.ipynb -p p=0.5 -p n=200
```

This will execute the notebook with the default configuration and, when the execution is complete, will download the resulting notebook. There are a lot of options to this command. Run `run-notebook run --help` for details.

#### 5. Run a notebook on a schedule

```sh
$ run-notebook schedule --at "cron(15 1 * * ? *)" --name nightly weather.ipynb -p "name=Boston, MA"
```

Note that times are always in UTC. To see the full rules on times, view the Cloudwatch Events documentation here: [Schedule Expressions for Rules][sched]

#### 6. See the jobs that have run and retrieve output

To see all the notebook executions that were run by the previous rule:

```sh
$ run-notebook list-runs --rule nightly
```

Each listed run will have a name. To download the result notebook, run:

```sh
$ run-notebook download jobname
```

## Activating the JupyterLab extension

The JupyterLab extension is included in the convenience package, so start by doing steps 1-3 in [Using the CLI provided by the convenience package](#using-the-cli-provided-by-the-convenience-package) above.

Once you have the infrastructure and containers set up, the best way to activate the extension will depend on your context.

#### In a SageMaker Notebook instance

1. Upload the provided library file, sagemaker_run_notebook-0.13.0.tar.gz, to a location of your choosing in S3.
2. On the AWS SageMaker console, go to Lifecycle Configuration. Create a new lifecycle configuration and add the `start.sh` script that you received in this distribution to the start action. Edit the S3 location to where you uploaded the installation tar file.
3. Start or restart your notebook instance after setting the lifecycle configuration to point at your newly created lifecycle configuration.

#### In SageMaker Studio

When you open SageMaker Studio, you can add the extension with the following steps:

1. Upload the provided library file, sagemaker_run_notebook-0.13.0.tar.gz, to a location of your choosing in S3.
2. Save the provided `install-run-notebook.sh` to your home directory in Studio. The easiest way to do this is to open a text file and paste the contents in. Then edit the S3 location to where you uploaded the installation tar file and save it as `install-run-notebook.sh`.
3. Open a terminal tab (`File`->`New`->`Terminal`) and run the script as `bash install-run-notebook.sh`.
4. When it's complete, refresh your Studio browser tab and you'll see the sidebar scheduler tab.

If you restart your server app, just rerun steps 3 & 4 and you'll have the extension ready to go.

#### On a laptop or other system

On your laptop, shutdown your Jupyter server process and run:

```sh
$ jupyter lab build
```

and then restart the server with:

```sh
$ jupyter lab
```

#### Using the JupyterLab extension

The JupyterLab extension feature adds a tab to the left sidebar in JupyterLab that lets you launch notebook executions, set up schedules, and view notebook runs and active schedules:

![JupyterLab sidebar](images/sidebar2.png)

From the "Runs" panel, you can monitor your active runs and open the output of completed runs directly into Jupyter, viewing, modifying, running, and saving the results:

![JupyterLab runs panel](images/runs-2.png)