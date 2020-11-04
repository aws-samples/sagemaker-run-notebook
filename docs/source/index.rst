.. sagemaker-run-notebook documentation master file, created by
   sphinx-quickstart on Mon Oct 26 10:50:40 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

sagemaker-run-notebook - Execute headless Jupyter Notebooks using Amazon SageMaker
==================================================================================

This library provides a set of tools that allow you to run and schedule Jupyter notebooks using
SageMaker Processing jobs. There are three ways to use these tools: a command-line tool, a Python
library, and a JupyterLab extension that provides a full graphical interface. You can use all these
ways in tandem. For example, you can use ``run-notebook run --no-wait mynotebook.ipynb`` to launch
a notebook run and use the "Notebook Runs" panel in JupyterLab to monitor the job and open the resulting
output notebook.

Setting up the library
----------------------

**TL;DR**: Use the QuickStart_.

There are two prerequisites to using the library in any of the forms:

1. Use CloudFormation to create the "infrastructure" to run and schedule jobs. This includes a Lambda function
   and a set of IAM policies and roles that give the minimal permissions needed to execute.
2. Create a Docker container with everything in it that your job needs to run.

Don't panic! The command line tool makes it very easy to do both these things.

To get everything set up and run your first commands, see the QuickStart_.


Detailed documentation
----------------------

.. toctree::
   :maxdepth: 2

   cli/index
   api/index
  
Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _QuickStart: https://github.com/aws-samples/sagemaker-run-notebook/blob/master/QuickStart.md