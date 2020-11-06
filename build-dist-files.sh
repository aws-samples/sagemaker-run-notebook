#!/bin/bash

# While this program is still private, I'm building a few artifacts that I can email around
# 1. This ReadMe with instructions and the newer QuickStart
# 2. The `sagemaker_run_notebook-${VERSION}.tar.gz` tar file that contains the library and the plugin.
# 3. The `start.sh` file to use as a lifecycle configuration script if you're using SageMaker notebook instances.
# 4. The `install-run-notebook.sh` file to use as an install script for the extension in SageMaker Studio
# 5. The `container.tar.gz` tar file contains what you need to build a Docker container for executing the notebooks with custom dependencies.
# 6. The `cloudformation.yml` for setting up all the roles, policies, and the Lambda functions
#
# They all live in the subdirectory "manual_dist/"

VERSION=0.18.0

make artifacts docs

rm -rf manual_dist
mkdir -p manual_dist

cp build/dist/sagemaker_run_notebook-${VERSION}.tar.gz manual_dist/
cp scripts/lifecycle-config/start.sh manual_dist/
cp scripts/studio/install-run-notebook.sh manual_dist/
gtar czf manual_dist/container.tar.gz container
cp sagemaker_run_notebook/cloudformation.yml manual_dist/
(cd docs/build/html; gtar czf ../../../manual_dist/docs.tar.gz --transform 's,^\./,sagemaker-run-notebook-docs/,' .)
