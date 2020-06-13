#!/usr/bin/env bash

# The argument to this script is the image name. This will be used as the image on the local
# machine and combined with the account and region to form the repository name for ECR.

prog=$0
default_image="python:3.7-slim-buster"

function usage {
    echo "Usage: $1 [--base <base-image>] <image>"
    echo "       base:  the image to use to build from [default: ${default_image}]"
    echo "       image: the image to build to. Will be pushed to the matching ECR repo in your account"
}

if [ "$1" == "--base" ]
then
    base=$2
    if [ "${base}" == "" ]
    then
       usage ${prog}
       exit 1
    fi
    shift 2
else
    base=${default_image}
fi

image=$1

if [ "${image}" == "" ]
then
    usage ${prog}
    exit 1
fi

echo "Source image ${base}"
echo "Final image ${image}"

# Get the account number associated with the current IAM credentials
account=$(aws sts get-caller-identity --query Account --output text)

if [ $? -ne 0 ]
then
    exit 255
fi


# Get the region defined in the current configuration (default to us-west-2 if none defined)
region=$(aws configure get region)
region=${region:-us-west-2}
echo "Region ${region}"


fullname="${account}.dkr.ecr.${region}.amazonaws.com/${image}:latest"

# If the repository doesn't exist in ECR, create it.

aws ecr describe-repositories --repository-names "${image}" > /dev/null 2>&1

if [ $? -ne 0 ]
then
    aws ecr create-repository --repository-name "${image}" > /dev/null
    if [ $? -ne 0 ]
    then
        exit 255
    fi
fi

# Docker login has changed in aws-cli version 2. We support both flavors.
AWS_CLI_MAJOR_VERSION=$(aws --version | sed 's%^aws-cli/\([0-9]*\)\..*$%\1%')
if [ "${AWS_CLI_MAJOR_VERSION}" == "1" ]
then
  # Get the login command from ECR and execute it directly
  $(aws ecr get-login --region ${region} --no-include-email)
else
  aws ecr get-login-password --region ${region} | docker login --username AWS --password-stdin ${account}.dkr.ecr.${region}.amazonaws.com
fi

# Build the docker image locally with the image name and then push it to ECR
# with the full name.

docker build -t ${image} --build-arg BASE_IMAGE=${base} .

docker tag ${image} ${fullname}

docker push ${fullname}
