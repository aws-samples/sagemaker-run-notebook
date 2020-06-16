## Lifecycle configuration for SageMaker notebook instances

This directory has a lifecycle configuration script that lets you set up the JupyterLab extension for scheduling notebooks in you SageMaker notebook instance.

To use this lifecycle configuration, perform the following steps:

1. Use the [AWS CLI][1] to copy the SageMaker Run Notebook tar file to a location in S3, for example `aws s3 cp sagemaker_run_notebook-0.13.0.tar.gz s3://my-bucket/some-path/`
2. Edit `start.sh` to point at the s3 location and correct plugin version from the previous step.
3. On the SageMaker AWS console, select "Lifecycle configurations" in the left column and create a new lifecycle configuration called `install-run-notebook-extension`. Copy the contents of `start.sh` into the "Start Notebook" script. You can leave the "Create Notebook" script blank.
4. When creating a new notebook instance, open the "Additional configuration" option in the "Notebook instance settings" and select the `install-run-notebook-extension`. You can also add this configuration to an existing notebook instance by stopping the instance, opening the instance on the console (by clicking on the instance name in the list of instances), and adding the new configuration there. Then restart your notebook instance.

For more information about lifecycle configurations, see ["Customize a Notebook Instance Using a Lifecycle Configuration Script"][2] in the AWS documentation.

[1]: https://aws.amazon.com/cli/
[2]: https://docs.aws.amazon.com/sagemaker/latest/dg/notebook-lifecycle-config.html
