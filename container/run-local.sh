#!/bin/bash

# Use the container locally to run a Jupyter notebook against a container

image=$1
notebook=$2
outdir=${3:-$(pwd)}

notebook_dir=$(dirname ${notebook})
notebook_file=$(basename ${notebook})

notebook_ext="${notebook_file##*.}"
notebook_base="${notebook_file%.*}"

docker run --rm \
       -v ${notebook_dir}:/opt/ml/processing/input \
       -v ${outdir}:/opt/ml/processing/output \
       -e PAPERMILL_INPUT=/opt/ml/processing/input/${notebook_file} \
       -e PAPERMILL_OUTPUT=/opt/ml/processing/output/${notebook_base}-$(date +%Y-%m-%d-%H-%M-%S).${notebook_ext} \
       -e PAPERMILL_PARAMS="{}" \
       ${image} run_notebook
