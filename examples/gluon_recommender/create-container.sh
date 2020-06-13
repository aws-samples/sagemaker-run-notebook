#!/bin/bash

region=us-west-2

aws ecr get-login-password --region ${region} | docker login --username AWS --password-stdin 763104351884.dkr.ecr.${region}.amazonaws.com

mkdir -p container

cd container

(cd ../../../container/; tar cf - .) | tar xf -

cp ../requirements.txt .

./build_and_push.sh --base 763104351884.dkr.ecr.${region}.amazonaws.com/mxnet-training:1.6.0-gpu-py36-cu101-ubuntu16.04 gluon-runner-gpu
