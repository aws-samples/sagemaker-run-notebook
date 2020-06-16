## SageMaker Run Notebook

> _Note_: sagemaker_run_notebook is experimental software designed for trial use. It may change significantly in the future and there is no guarantee of support. Please do use it and give us feedback on what we could improve, but take its experimental nature into account.

This is a library and a JupyterLab extension that lets you run your Jupyter Notebooks in AWS using SageMaker processing jobs. Notebooks can be run on a schedule, triggered by an event, or called _ad hoc_. Notebooks are executed using [papermill](https://github.com/nteract/papermill) which allows you to specify parameters for each notebook run.

In addition to running notebooks, the library has tools to visualize runs and download the output notebooks. Notebooks can mark output data using [scrapbook](https://github.com/nteract/scrapbook) and that data can be retrieved from a single run or across several runs.

### Getting Started

There are various ways to use the tools provided here, each with a slightly different set up.

1. You can create the infrastructure you need with the provided CloudFormation template and then use standard AWS APIs to schedule, run, and monitor your notebooks. This is a good route when you don't want to add unsupported dependencies or you want to perform these actions from a language other than Python.
2. You can perform operations from the shell using a command-line interface design explicitly for running notebooks (_e.g._, `$ run-notebook run weather.ipynb -p place="Seattle, WA"`).
3. You can perform operations from a Jupyter notebook or Python program using a special Python library (_e.g._, `run.invoke(notebook="weather.ipynb", parameters={"place": "Seattle, WA"})`)
4. You can use the JupyterLab extension to run, schedule, and monitor notebooks interactively in any JupyterLab environment (inluding SageMaker Studio and SageMaker notebook instances)

For options 2-4, you'll install the Python convenience package that's part of the repository.

To install and configure the tools, see the [Quick Start](QuickStart.md).

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
