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

.PHONY: clean artifacts release link install test run cfntemplate

release: install test
	make artifacts

install: clean
	# Use the -e[dev] option to allow the code to be instrumented for code coverage
	pip install -e ".[dev]"
	jupyter serverextension enable --py sagemaker_run_notebook --sys-prefix

clean:
	rm -f sagemaker_run_notebook/cloudformation.yml
	rm -rf build/dist

cfntemplate: sagemaker_run_notebook/cloudformation.yml

sagemaker_run_notebook/cloudformation.yml: sagemaker_run_notebook/cloudformation-base.yml sagemaker_run_notebook/lambda_function.py
	pyminify sagemaker_run_notebook/lambda_function.py | sed 's/^/          /' > /tmp/minified.py
	cat sagemaker_run_notebook/cloudformation-base.yml /tmp/minified.py > sagemaker_run_notebook/cloudformation.yml

artifacts: clean cfntemplate
	python setup.py sdist --dist-dir build/dist

test:
  # No python tests implemented yet
	# pytest -v .
	black --check .
