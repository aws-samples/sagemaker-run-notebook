#!/bin/bash

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

set -e

# OVERVIEW
# This script installs the sagemaker_run_notebook extension package in SageMaker Notebook Instance
#

sudo -u ec2-user -i <<'EOF'

# PARAMETERS
VERSION=0.23.0

EXTENSION_NAME=sagemaker_run_notebook

# Set up the user setting and workspace directories
mkdir -p /home/ec2-user/SageMaker/.jupyter-user/{workspaces,user-settings}

# Run in the conda environment that the Jupyter server uses so that our changes are picked up
source /home/ec2-user/anaconda3/bin/activate JupyterSystemEnv

# Install the extension and rebuild JupyterLab so it picks up the new UI
pip install https://github.com/aws-samples/sagemaker-run-notebook/releases/download/v${VERSION}/sagemaker_run_notebook-${VERSION}.tar.gz

conda deactivate
EOF

# Tell Jupyter to use the user-settings and workspaces directory on the EBS
# volume.
echo "export JUPYTERLAB_SETTINGS_DIR=/home/ec2-user/SageMaker/.jupyter-user/user-settings" >> /etc/profile.d/jupyter-env.sh
echo "export JUPYTERLAB_WORKSPACES_DIR=/home/ec2-user/SageMaker/.jupyter-user/workspaces" >> /etc/profile.d/jupyter-env.sh

# The Jupyter server needs to be restarted to pick up the server part of the
# extension. This needs to be done as root.

notebook_pid=$(ps -eflww | awk '$16 ~ /jupyter-nbclassic$/ {print $4}')
if [ "${notebook_pid}" != "" ]
then
    echo "restarting Jupyter server"
    kill ${notebook_pid}
else
    echo "Jupyter server not running, no need to restart"
fi
