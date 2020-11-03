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

__all__ = [
    "invoke",
    "wait_for_complete",
    "stop_run",
    "list_runs",
    "describe_run",
    "describe_runs",
    "schedule",
    "unschedule",
    "list_schedules",
    "describe_schedule",
    "describe_schedules",
    "upload_notebook",
    "upload_fileobj",
    "download_notebook",
    "download_all",
    "InvokeException",
    "NotebookRunTracker",
]
from sagemaker_run_notebook.run_notebook import (
    create_lambda,
    create_lambda_role,
    schedule,
    unschedule,
    describe_schedule,
    describe_schedules,
    list_schedules,
    invoke,
    run_notebook,
    upload_notebook,
    upload_fileobj,
    download_notebook,
    download_all,
    wait_for_complete,
    list_runs,
    describe_run,
    describe_runs,
    stop_run,
    InvokeException,
    NotebookRunTracker,
)

from sagemaker_run_notebook.server_extension._version import __version__

has_jupyter = False
try:
    import notebook

    has_jupyter = True
except ModuleNotFoundError:
    pass

if has_jupyter:
    """Initialize the backend server extension, if jupyter is installed."""
    # need this in order to show version in `jupyter serverextension list`
    from sagemaker_run_notebook.server_extension._version import __version__

    from sagemaker_run_notebook.server_extension.handlers import setup_handlers
    from sagemaker_run_notebook.server_extension.run import Scheduler

    def _jupyter_server_extension_paths():
        """Declare the Jupyter server extension paths."""
        return [{"module": "sagemaker_run_notebook"}]

    def load_jupyter_server_extension(nbapp):
        """Load the Jupyter server extension."""
        scheduler = Scheduler(nbapp.web_app.settings["contents_manager"])
        nbapp.web_app.settings["scheduler"] = scheduler
        setup_handlers(nbapp.web_app)
