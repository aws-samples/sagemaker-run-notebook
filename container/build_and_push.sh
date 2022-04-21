#!/usr/bin/env bash

# The argument to this script is the image name. This will be used as the image on the local
# machine and combined with the account and region to form the repository name for ECR.
set -a
set -euo pipefail


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

IMAGE_NAME=$1

if [ "${IMAGE_NAME}" == "" ]
then
    usage ${prog}
    exit 1
fi

echo "Source image ${base}"
echo "Final image ${IMAGE_NAME}"

# Get the account number associated with the current IAM credentials
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ $? -ne 0 ]
then
    exit 255
fi

DATE=$(date +%Y%m%d%H%M%S)

TAG=${2:-$DATE}


# Get the region defined in the current configuration (default to ap-southeast-2 if none defined)
AWS_REGION=$(aws configure get region)
AWS_REGION=${AWS_REGION:-ap-southeast-2}
echo "Region ${AWS_REGION}"

AWS_PROFILE=${3:-'relevanceai'}


DATE=$(date +%Y%m%d%H%M%S)

ECR_REPOSITORY_URI="${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REPOSITORY_URI}/${IMAGE_NAME}"
echo $ECR_REPOSITORY_URI
echo $IMAGE_URI


# If the repository doesn't exist in ECR, create it.

aws --profile ${AWS_PROFILE} ecr describe-repositories --repository-names "${IMAGE_NAME}" > /dev/null 2>&1

if [ $? -ne 0 ]
then
    aws --profile ${AWS_PROFILE} ecr create-repository --repository-name "${IMAGE_NAME}" > /dev/null
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
  $(aws --profile ${AWS_PROFILE} ecr get-login --region ${AWS_REGION} --no-include-email)
else
  aws --profile ${AWS_PROFILE} ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
fi

# Build the docker image locally with the image name and then push it to ECR
# with the full name.

docker build -t ${IMAGE_NAME} --build-arg BASE_IMAGE=${base} .

echo "Tagging IMAGE_NAME ${IMAGE_URI}:${TAG}"
echo "Tagging IMAGE_NAME ${IMAGE_URI}:latest"
docker tag ${IMAGE_NAME} "${IMAGE_URI}:${TAG}"
docker tag ${IMAGE_NAME} "${IMAGE_URI}:latest"

echo "Pushing IMAGE_NAME to ECR ${IMAGE_URI}"
docker push "${IMAGE_URI}:${TAG}"
docker push "${IMAGE_URI}:latest"
# docker tag ${IMAGE_NAME} ${fullname}

# docker push ${fullname}
