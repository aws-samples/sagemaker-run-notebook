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

# Support for adding extra options to the run to connect to an EMR cluster.
# Note that the cluster information is when the function is called, not when
# the notebook is run.

import itertools as it
import boto3


def ensure_session(session=None):
    """If session is None, create a default session and return it. Otherwise return the session passed in"""
    if session is None:
        session = boto3.session.Session()
    return session


def get_cluster_info(cluster_name, session=None):
    """Get the information about a running cluster so that the processing job can be connected to it.

    Args:
        cluster_name (str): The name of a running EMR cluster to connect to (required).
        session (boto3.Session): The boto3 session to use. Will create a default session if not supplied (default: None).

    Returns:
        tuple: A tuple with cluster DNS address, the security group, and the subnet.
    """
    session = ensure_session(session)
    emr = session.client("emr")

    id = None
    marker = None

    while True:
        if marker:
            marker_args = dict(Marker=marker)
        else:
            marker_args = {}
        list_results = emr.list_clusters(
            ClusterStates=["STARTING", "BOOTSTRAPPING", "RUNNING", "WAITING"],
            **marker_args
        )
        marker = list_results.get("Marker")
        cluster_info = list(
            it.islice(
                filter(
                    lambda c: c.get("Name") == cluster_name, list_results["Clusters"]
                ),
                1,
            )
        )
        if cluster_info:
            id = cluster_info[0]["Id"]
            break
        elif not marker:
            break

    if not id:
        raise RuntimeError('Active cluster named "{}" not found'.format(cluster_name))

    desc = emr.describe_cluster(ClusterId=id)
    dns_addr = desc["Cluster"]["MasterPublicDnsName"]
    sg = desc["Cluster"]["Ec2InstanceAttributes"]["EmrManagedMasterSecurityGroup"]
    subnet = desc["Cluster"]["Ec2InstanceAttributes"]["Ec2SubnetId"]

    return dns_addr, sg, subnet


def add_emr_cluster(cluster):
    "An options function to add the EMR cluster arguments to an extra block"
    master_addr, sg, subnet = get_cluster_info(cluster)

    def proc(extra):
        env = extra.get("Environment", {})  # There may or may not already be env vars
        env["EMR_ADDRESS"] = master_addr
        extra["Environment"] = env

        net = extra.get("NetworkConfig", {})
        if net.get("VpcConfig"):
            raise RuntimeError(
                "Can't add EMR cluster if there's already a VPC connection specified"
            )
        net["VpcConfig"] = dict(SecurityGroupIds=[sg], Subnets=[subnet])
        extra["NetworkConfig"] = net
        return extra

    return proc
