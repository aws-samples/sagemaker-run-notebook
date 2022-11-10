# Quick Start

> __TL;DR__ To be really quick, go straight to the instructions at [Setting up your environment](#setting-up-your-environment).

This document shows how to install and run the `sagemaker-run-notebooks` library that lets you run and schedule Jupyter notebook executions as SageMaker Processing Jobs.

This library provides three interfaces to the notebook execution functionality:

1. A command line interface (CLI)
2. A Python library
3. A JupyterLab extension that can be enabled for JupyterLab running locally, in SageMaker Studio, or on a SageMaker notebook instance

Each of the interfaces has the same functionality, so which to use is a matter of preference. You can use them in combination if you choose. For example, you can launch a notebook execution from the CLI, but monitor and view the output using the JupyterLab extension.

We use the open source tool [Papermill][papermill] to execute the notebooks. Papermill has many features, but one of the most interesting is that you can add parameters to your notebook runs. To do this, you set a tag on a single cell in your notebook that marks it as the "parameter cell". Papermill will insert a cell directly after that at runtime with the parameter values you set when starting the job. You can see details in the Papermill docs [here][papermill-parameters].

More detailed documentation, including full API documentation for the library and all the options for the
can be downloaded as HTML files from the [latest GitHub release][release]. Download `docs.tar.gz` and untar it with `tar xzf docs.tar.gz`. Then open the file `sagemaker-run-notebook-docs/index.html` in your browser
to view the documentation.

[papermill]: https://github.com/nteract/papermill
[papermill-parameters]: https://papermill.readthedocs.io/en/latest/usage-parameterize.html

Start by setting up your environment and then look at the instructions for the interface you want to use.

Contents:

- [Quick Start](#quick-start)
  - [Setting up your environment](#setting-up-your-environment)
      - [1. Install the library](#1-install-the-library)
      - [2. Create roles, policies and the Lambda function](#2-create-roles-policies-and-the-lambda-function)
      - [3. Create a Docker container to run the notebook](#3-create-a-docker-container-to-run-the-notebook)
  - [Use the command-line tool to execute and schedule notebooks](#use-the-command-line-tool-to-execute-and-schedule-notebooks)
      - [Run a notebook on demand](#run-a-notebook-on-demand)
      - [Run a notebook on a schedule](#run-a-notebook-on-a-schedule)
      - [See the jobs that have run and retrieve output](#see-the-jobs-that-have-run-and-retrieve-output)
  - [Using the Python library](#using-the-python-library)
  - [Activating the JupyterLab extension](#activating-the-jupyterlab-extension)
      - [In a SageMaker Notebook instance](#in-a-sagemaker-notebook-instance)
      - [In SageMaker Studio](#in-sagemaker-studio)
      - [On a laptop or other system](#on-a-laptop-or-other-system)
  - [Using the JupyterLab extension](#using-the-jupyterlab-extension)

The files we reference here can be downloaded from the [latest GitHub release][release].

__Note:__ The JupyterLab extension in the current release supports JupyterLab 3.x releases. If you're running 
an older version of JupyterLab and want to use GUI interface, use one of the following older releases of the extension:

| JupyterLab Version | Extension Release       |
| ------------------ | ----------------------- |
|       3.x          | [latest][release]       |
|       2.x          | [v0.23.0][release-2.x]  |
|       1.x          | [v0.19.0][release-1.x]  |

If you want to schedule notebooks without using the library, there are resources included in the
release to help you do that. See the [DIY instructions][DIY] on GitHub for details.

[release]: https://github.com/aws-samples/sagemaker-run-notebook/releases/latest
[release-1.x]: https://github.com/aws-samples/sagemaker-run-notebook/releases/tag/v0.19.0
[release-2.x]: https://github.com/aws-samples/sagemaker-run-notebook/releases/tag/v0.23.0
[DIY]: https://github.com/aws-samples/sagemaker-run-notebook/blob/master/DIY.md

## Setting up your environment

To follow this recipe, you'll need to have AWS credentials set up that give you full permission on CloudFormation. You'll add more permissions with the installed policy later in the recipe.

#### 1. Install the library

You can install the library directly from the GitHub release using pip:

```sh
$ pip install https://github.com/aws-samples/sagemaker-run-notebook/releases/download/v0.23.0/sagemaker_run_notebook-0.23.0.tar.gz
```

This installs the sagemaker-run-notebook library, CLI tool and the JupyterLab 3.x plug-in. After installation, you will need to restart any currently running JupyterLab servers to activate the plug-in.

To create a persistent installation (one that survives across restarts) in SageMaker notebook instances and SageMaker Studio notebooks, see below in [Activating the JupyterLab Extension](#activating-the-jupyterlab-extension).

#### 2. Create roles, policies and the Lambda function

```sh
$ run-notebook create-infrastructure
```

One of the policies created here is `ExecuteNotebookClientPolicy-us-east-1` (replace `us-east-1` with the name of the region you're running in). If you're not running with administrative permissions, you should add that policy to the user or role that you're using to invoke and schedule notebooks.

For complete information on the roles and policies, see the [`cloudformation-base.yml` on GitHub][cfn-template].
The source code for the Lambda function is at [`lambda-function.py` on GitHub][lambda-function].

[cfn-template]: https://github.com/aws-samples/sagemaker-run-notebook/blob/master/sagemaker_run_notebook/cloudformation-base.yml
[lambda-function]: https://github.com/aws-samples/sagemaker-run-notebook/blob/master/sagemaker_run_notebook/lambda_function.py

#### 3. Create a Docker container to run the notebook

Jobs run in SageMaker Processing Jobs run inside a Docker container. For this project, we have defined
the container to include a script to set up the environment and run Papermill on the
input notebook.

```sh
$ run-notebook create-container
```

This creates a temporary project in AWS CodeBuild to build your Docker container image so there's no need
to install Docker locally.

_Optional_: If you want to add custom dependencies to your container, you can create a requirements.txt file as
described at [Requirements Files][requirements] in the `pip` documentation. Then add that to your CLI command
like this:

```sh
$ run-notebook create-container --requirements requirements.txt
```

More customization is possible. Run `run-notebook create-container --help` or see the docs for more information.

If you'd rather do the Docker build on your local system, you can use the DIY recipe specified in [Create a container image to run your notebook][DIY-container].

[requirements]: https://pip.pypa.io/en/stable/user_guide/#requirements-files
[DIY-container]: https://github.com/aws-samples/sagemaker-run-notebook/blob/master/DIY.md#2-create-a-container-image-to-run-your-notebook

## Use the command-line tool to execute and schedule notebooks

To get information on how to use the CLI, run `run-notebook --help` or view the help documentation described above.

#### Run a notebook on demand

To run a notebook:

```sh
$ run-notebook run mynotebook.ipynb -p p=0.5 -p n=200
```

This will execute the notebook with the default configuration and, when the execution is complete, will download the resulting notebook. There are a lot of options to this command. Run `run-notebook run --help` for details.

#### Run a notebook on a schedule

```sh
$ run-notebook schedule --at "cron(15 1 * * ? *)" --name nightly weather.ipynb -p "name=Boston, MA"
```

Note that times are always in UTC. To see the full rules on times, view the Cloudwatch Events documentation here: [Schedule Expressions for Rules][sched]

[sched]: https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/ScheduledEvents.html

#### See the jobs that have run and retrieve output

To see all the notebook executions that were run by the previous rule:

```sh
$ run-notebook list-runs --rule nightly
```

Each listed run will have a name. To download the result notebook, run:

```sh
$ run-notebook download jobname
```

## Using the Python library

The Python library lets you interact with notebook execution directly from Python code, for example
in a Jupyter notebook or a Python program.

To use the library, just import it. These examples assume you import it as "run":

```python
import sagemaker_run_notebook as run
```

To run a notebook immediately and wait for the result, use `invoke()`, `wait_for_complete()`, 
and `download_notebook()`:

```python
job = run.invoke("powers.ipynb")
run.wait_for_complete(job)
run.download_notebook(job)
```

To schedule a notebook to run Sunday mornings at 3AM (UTC), use the `schedule()` function:

```python
run.schedule("powers.ipynb", rule_name="powers", schedule="cron(0 3 ? * SUN *)")
```

To see the last two scheduled runs for a rule:

```python
runs = run.list_runs(n=2, rule="powers")
runs
```

And to download the output notebooks:

```python
run.download_all(runs)
```

For full API documentation for the library, download the docs from the [latest release][release]
 and explore.

## Activating the JupyterLab extension

Once you have the infrastructure and containers set up, the best way to activate the extension will depend on your context.

#### In a SageMaker Notebook instance

If you are using SageMaker Notebook Instances, the extension can be enabled automatically by adding a Lifecycle Configuration and restarting your Notebook Instance. This is an easy process that can be done once on the AWS console. See the [ReadMe file][instance-lifecycle] for the instructions.

[instance-lifecycle]: https://github.com/aws-samples/sagemaker-run-notebook/blob/master/scripts/lifecycle-config/notebook-instances/ReadMe.md

#### In SageMaker Studio

If you use SageMaker Studio notebooks, the extension can be enabled by adding a Lifecycle Configuration to your Studio Domain and restarting any Jupyter server apps. This is an easy process that can be done once on the AWS console. See the [README file][studio-lifecycle] for the instructions.

[studio-lifecycle]: https://github.com/aws-samples/sagemaker-run-notebook/blob/master/scripts/lifecycle-configuration/studio/README.md

#### On a laptop or other system

Once you've installed the library with `pip install`, you'll need to restart your Jupyter server and refresh your web interface to pick up the extension in JupyterLab.

> __Note:__ This extension currently supports JupyterLab 3.x releases. For support for other JupyterLab versions, see the table at the top of the document.

## Using the JupyterLab extension

The JupyterLab extension feature adds a tab to the left sidebar in JupyterLab that lets you launch notebook executions, set up schedules, and view notebook runs and active schedules:

![JupyterLab sidebar](images/sidebar2.png)

From the "Runs" panel, you can monitor your active runs and open the output of completed runs directly into Jupyter, viewing, modifying, running, and saving the results:

![JupyterLab runs panel](images/runs-2.png)
