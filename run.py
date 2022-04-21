#!/usr/bin/env python3
# -*- coding:utf-8 -*-
#####
# Author: Charlene Leong charleneleong84@gmail.com
# Created Date: Wednesday, April 20th 2022, 2:51:50 pm
# Last Modified: Thursday, April 21st 2022,11:31:46 am
#####
import sagemaker_run_notebook as run

from pathlib import Path
NOTEBOOK_PATH=Path.cwd().joinpath("examples", "powers.ipynb")
EXECUTION_ROLE='arn:aws:iam::701405094693:role/BasicExecuteNotebookRole-ap-southeast-2'

print(f'NOTEBOOK_PATH: {NOTEBOOK_PATH}')
print('Invoking job ...')

job = run.invoke(NOTEBOOK_PATH, role=EXECUTION_ROLE)

print('Wait for job to complete ...')
run.wait_for_complete(job)

print('Download notebook ...')
run.download_notebook(job)