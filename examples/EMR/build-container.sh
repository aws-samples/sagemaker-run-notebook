#!/bin/bash

# Build a container to run a Spark Magic notebook to connect to an EMR cluster. 

usage(){
  cat <<EOF
Usage: $0 [options]

Options:
    -c | --cluster <cluster>     The EMR cluster for this container to connect to by default. (default: NONE)
    -i | --image <image-name>    The name of the ECR image to create. (default: emr-notebook-runner)
    -k | --kernel <kernel-name>  The kernel to use to run the notebook. (default: pysparkkernel)

  The EMR cluster can be specified using the cluster ID, the cluster name, or the DNS address of the main node. This will be
  converted to the DNS address internally, so if you destroy and recreate the cluster, you will need to rebuild the container
  even if the cluster has the same name.
EOF
	exit 1
}

function cluster_for(){
  local target=$1
  local addr=$(aws --output text emr describe-cluster --cluster-id "${target}" --query "Cluster.MasterPublicDnsName" 2>/dev/null)
  if [ "${addr}" == "" ]
  then
    local id=$(aws --output text emr list-clusters --active --query 'Clusters[*].{Id:Id,Name:Name}' | egrep "^[^\t]+\t${target}$" | cut -f1)
    if [ "${id}" == "" ]
    then
      if [[ ${target} =~ ^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$ ]]
      then
        # ${target} is a DNS name for the cluster
        echo ${target}
      else
        echo "${target} is not an valid cluster id, name, or address" 1>&2
        exit 1
      fi
    else
      addr=$(aws --output text emr describe-cluster --cluster-id "${id}" --query "Cluster.MasterPublicDnsName")
      # ${target} is a cluster name with cluster id ${id} and address ${addr}
      echo ${addr}
    fi
  else 
    # ${target} is an cluster id with address ${addr}
    echo ${addr}
  fi 
}

cluster=
image=emr-notebook-runner
kernel=pysparkkernel

while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -i|--image)
    image="$2"
    shift # past argument
    shift # past value
    ;;
    -c|--cluster)
    cluster="$2"
    shift # past argument
    shift # past value
    ;;
    -k|--kernel)
    kernel="$2"
    shift # past argument
    shift # past value
    ;;
    *)    # unknown option
    echo "Unknown argument $1"
    usage
    ;;
esac
done

INSTALL=install.sh

if [ "${cluster}" != "" ]
then
  addr=$(cluster_for "$cluster")
  if [ "$addr" == "" ]
  then
    exit 1
  fi

  TMPFILE=/tmp/install.sh.$$
  trap "{ rm -f $TMPFILE; }" EXIT
  sed "s/EMR_MASTER_IP=NONE/EMR_MASTER_IP=${addr}/" ${INSTALL} > ${TMPFILE}
  INSTALL=${TMPFILE}
fi
run-notebook create-container --script ${INSTALL} -k ${kernel} ${image}