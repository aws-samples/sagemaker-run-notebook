# Changelog

## v0.18.0 (2020-11-06)

This is a documentation only release:

* It adds the documentation tarball (`docs.tar.gz`) to the release.
* It adds reasonable docstrings to all the exported functions in `sagemaker_run_notebook`.

## v0.17.0 (2020-11-05)

Ignore. Not actually released.

## v0.16.0 (2020-10-23)

Users moving to this version should update their Lambda function and permissions by running:

```shell
$ run-notebook create-infrastructure --update
```

### Features

* Added the ability to run notebooks connected to an EMR cluster using SparkMagic. See the [EMR examples][EMR example] for more information on using this feature.
* Add the permissions to the default execution policy and role that allow notebook executions to attach to user VPCs via the `--extra` option.

[EMR example]: https://github.com/aws-samples/sagemaker-run-notebook/tree/master/examples/EMR

### Bug fixes

* Pass environment variables specified in `--extra` parameters through to the notebook execution.
* Restrict S3 permissions in the default role to buckets whose name contains the word "SageMaker".
* Unpin the version of the Python "requests" library because it is (a) no longer necessary and (b) cause a dependency error with the latest version of boto3.

## v0.15.0 (2020-09-23)

### Bugs

* Fixed [Issue #4](https://github.com/aws-samples/sagemaker-run-notebook/issues/4), a regression where the invocation of papermill would fail with "No such kernel". (Note that any containers built under v0.14.0, should be rebuilt with `run-notebook )

### Features

Two small changes:

* Added a `-v` option to run-notebook to display the current installed version of the library.
* Changed the install scripts for SageMaker notebooks to install directly from the release on GitHub so users don't need to copy to an S3 bucket first.

## v0.14.0 (2020-09-14)

### Features

* Run notebooks written in R or other languages. See the newly added [R example][example] for information.
* When using the CLI or Library, you can supply extra arguments to the SageMaker Processing Job used to execute the notebook. For example to allow your notebook to run for up to a full day, invoke your notebook with `run-notebook run foo.ipynb --extra '{"StoppingCondition":{"MaxRuntimeInSeconds":86400}}'`. Using this mechanism, you can add extra inputs and outputs, connect to a VPC, add environment variables, expand disk space, add the run to a specific experiment, etc. See the [documentation for SageMaker Processing Jobs][processing-jobs] for more.
  
[example]: https://github.com/aws-samples/sagemaker-run-notebook/tree/master/examples/R
[processing-jobs]: https://docs.aws.amazon.com/cli/latest/reference/sagemaker/create-processing-job.html

### Running Notebooks

* Add an option to pass extra parameters to SageMaker Processing jobs from the CLI/Library (not yet supported in the JupyterLab extension).
* Add the ability to use the CLI to run the notebook using local Docker containers (`run-notebook local`).

### Container building (`run-notebook create-container`)

* Support base containers from ECR repos in other AWS accounts (to enable using [AWS Deep Learning Containers][dlc]).
* Add the `-k` option to allow alternate Jupyter kernels
* Add the `--script` option for running arbitrary shell scripts as part of building the container.
* Tail the build logs when running the build so you can see any errors that happen inline.
* Automatically install Python if the base image doesn't already have it.

[dlc]: https://docs.aws.amazon.com/deep-learning-containers/latest/devguide/deep-learning-containers-images.html

### JupyterLab Extension

* Fixes for running in Safari

## v0.13.0 (2020-06-15)

Initial release.
