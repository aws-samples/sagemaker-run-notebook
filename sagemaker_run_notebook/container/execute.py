#!/usr/bin/env python

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

from __future__ import print_function

import os
import json
import sys
import traceback
from urllib.parse import urlparse
from urllib.request import urlopen

import boto3
import botocore

import jupyter_client.kernelspec as kernelspec

import papermill

input_var = "PAPERMILL_INPUT"
output_var = "PAPERMILL_OUTPUT"
params_var = "PAPERMILL_PARAMS"


def run_notebook():
    try:
        notebook = os.environ[input_var]
        output_notebook = os.environ[output_var]
        params = json.loads(os.environ[params_var])

        notebook_dir = os.path.dirname(notebook)
        notebook_file = os.path.basename(notebook)

        # If the user specified notebook path in S3, run with that path.
        if notebook.startswith("s3://"):
            print("Downloading notebook {}".format(notebook))
            o = urlparse(notebook)
            bucket = o.netloc
            key = o.path[1:]

            s3 = boto3.resource("s3")

            try:
                s3.Bucket(bucket).download_file(key, "/tmp/" + notebook_file)
                notebook_dir = "/tmp"
            except botocore.exceptions.ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    print("The notebook {} does not exist.".format(notebook))
                raise
            print("Download complete")

        os.chdir(notebook_dir)

        kernel = os.environ.get("PAPERMILL_KERNEL", None)
        if not kernel:
            nb_kernel = kernel_for(notebook_file)
            avail_kernels = available_kernels()
            if nb_kernel is None or nb_kernel not in avail_kernels:
                kernel = avail_kernels[0]
            else:
                kernel = nb_kernel

        print(
            "Executing {} with output to {}{}".format(
                notebook_file,
                output_notebook,
                (" using kernel " + kernel) if kernel else "",
            )
        )
        print("Notebook params = {}".format(params))
        arg_map = dict(kernel_name=kernel) if kernel else {}
        papermill.execute_notebook(
            notebook_file,
            output_notebook,
            params,
            **arg_map,
        )
        print("Execution complete")

    except Exception as e:
        # Write out an error file. This will be returned as the failureReason in the
        # DescribeProcessingJob result.
        trc = traceback.format_exc()
        # with open(os.path.join(output_path, 'failure'), 'w') as s:
        #    s.write('Exception during processing: ' + str(e) + '\n' + trc)
        # Printing this causes the exception to be in the training job logs, as well.
        print("Exception during processing: " + str(e) + "\n" + trc, file=sys.stderr)
        # A non-zero exit code causes the training job to be marked as Failed.
        # sys.exit(255)
        output_notebook = "xyzzy"  # Dummy for print, below

    if not os.path.exists(output_notebook):
        print("No output notebook was generated")
    else:
        print("Output was written to {}".format(output_notebook))


def available_kernels():
    """Return the list of kernels"""
    mgr = kernelspec.KernelSpecManager()
    return list(mgr.find_kernel_specs().keys())


def kernel_for(notebook):
    """Read the notebook and extract the kernel name, if any"""
    with open(notebook, "r") as f:
        nb = json.load(f)

        md = nb.get("metadata")
        if md:
            ks = md.get("kernelspec")
            if ks:
                return ks["name"]
    return None


if __name__ == "__main__":
    run_notebook()
