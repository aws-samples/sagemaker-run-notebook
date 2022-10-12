## Lifecycle configuration for SageMaker Studio notebooks

This directory has a lifecycle configuration script that lets you set up the JupyterLab extension for scheduling notebooks in your SageMaker Studio notebook.

To use this lifecycle configuration, perform the following steps:

1. **Create the Lifecycle Configuration**: On the SageMaker AWS console, select "Lifecycle configurations" in the left column, then choose the "Studio" tab. Press "Create configuration". Start by choosing "Jupyter server app" from the "Select configuration type" page and press "Next". Enter `install-run-notebook-extension` in the name field and copy the contents of `install-run-notebook.sh` into the "Scripts" text box. Press "Create Configuration".
2. **Attach the Lifecycle Configuration to your Studio domain**: On the SageMaker AWS console, select "Control panel" in the left column. Scroll to the bottom and click on the "Lifecycle configurations". Click on the "Attach" button to open the attach panel. Click on the check box next to `install-run-notebook-extension` and click on "Attach to domain" to attach it. **Very important**: You're not done yet. Back on the "Control panel" page, select the checkbox by the `install-run-notebook-extension` lifecycle configuration, then click "Set as default" to make Studio run the script on start up.
3. **Restart any running Studio sessions**: If you want the GUI to appear in Studio sessions that you've already started, restart the notebook server app from the control panel. To do this, you can shutdown the notebook server from the "File" menu in JupyterLab and then reopen it.

For more information about lifecycle configurations, see ["Use Lifecycle Configurations with Amazon SageMaker Studio"][1] in the AWS documentation.

[1]: https://docs.aws.amazon.com/sagemaker/latest/dg/studio-lcc.html
