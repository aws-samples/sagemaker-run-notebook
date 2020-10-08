# Running SparkMagic Notebooks connected to EMR

When running interactive notebooks in SageMaker, you can use [SparkMagic][SparkMagic] to connect to a running EMR system and run Spark jobs. Then you can retrieve, analyze, and visualize the results in your notebook. Instructions on how to do this are available in the blog post [Build Amazon SageMaker notebooks backed by Spark in Amazon EMR][SageMakerNotebook-SparkMagic].

Often, we find that once we've got the Spark program set up, we want to run that program on a schedule or in response to an event.  

Using `run-notebook`, we can do just that.

To use `run-notebook` to execute sparkmagic-based notebooks connected to EMR clusters, you'll need to:

1. Create a container for running the notebook. See [Build a container](#build-a-container).
2. Execute or schedule the notebook using `run-notebook`. See [Run the notebook](#run-the-notebook).

It is not yet possible to set up EMR connections from the JupyterLab GUI.

[SparkMagic]: https://github.com/jupyter-incubator/sparkmagic
[SageMakerNotebook-SparkMagic]: https://aws.amazon.com/blogs/machine-learning/build-amazon-sagemaker-notebooks-backed-by-spark-in-amazon-emr/

### Build a container

As a convenience, we provide the shell script [`build-container.sh`](build-container.sh) here. This script takes three options: the target image name, the sparkmagic kernel to use, and the default EMR cluster to connect to.

The __image name__, specified with the `-i` option, is the name of the ECR repository in your account in which to store the created image. If not specified, the name "emr-notebook-runner" is used.

The __sparkmagic kernel__, specified with the `-k` option, can be "pysparkkernel" for Python-based notebooks (the default), "sparkkernel" for Scala-based notebooks, or "sparkrkernel" for R-based notebooks. 

The __cluster__, specified with the `-c` option, indicates the name of an active EMR cluster to use for connections. By default, no cluster is specified and it must be specified at runtime. __Note 1:__ Cluster is resolved when you build the container and the EMR master public DNS address is determined at that time. If the cluster is terminated and a new one is created with the same name, you'll need to rebuild the container. __Note 2:__ Only the cluster master public DNS is added to the container image. You'll still need to use the `--extra` argument to `run-notebook` to attach the notebook to the VPC for the cluster.

The container built with the script uses the Python 3 default base image.

You can run the script with no arguments:

```shell
$ ./build-container.sh
```

which builds a container image called "emr-notebook-runner" that runs a pyspark notebook. The name of the EMR cluster must be specified when you call `run-notebook` (see below). Note that you must have specified AWS credentials in your configuration or in your environment.

If you run the build like this:

```shell
$ ./build-container.sh -c "Data Analysis Cluster" -i analysis-notebook-runner -k sparkkernel
```

you will build a container image called "analysis-notebook-runner" which runs a Spark Scala kernel connected to the cluster called "Data Analysis Cluster".

[1]: https://github.com/jupyter/docker-stacks/tree/master/r-notebook

### Run the notebook

As mentioned above, you currently need to use the `run-notebook` command to run notebooks connected to EMR. The JupyterLab GUI doesn't have the ability to pass the extra arguments that you need.

For example, to run the PySpark sample notebook included here using the cluster called "LivyTestCluster", you can simply run the following command:

```shell
$ run-notebook run spark-test.ipynb -p input="s3://mybucket/myfile.txt" --image emr-notebook-runner --emr LivyTestCluster
```

Make sure to specify a real text file that you've put in S3.

The `--emr` argument will call EMR and get the information about the cluster to pass to the notebook execution. If you don't have EMR permissions where you're running `run-notebook`, you can pass the parameters in explicitly with the `--extra` option:

```shell
$ run-notebook run spark-test.ipynb -p input="s3://mybucket/myfile.txt" \
      --image emr-notebook-runner \
      --extra '{"Environment": {"EMR_ADDRESS": "ec2-54-195-170-239.us-west-2.compute.amazonaws.com"}, \
                "NetworkConfig":{"VpcConfig":{"SecurityGroupIds":["sg-xxxxxxxx"],\
                                              "Subnets":["subnet-xxxxxxxx"]}}}'
```

substituting appropriate values for your cluster.

The same idea works for scheduling notebook executions. To run the PySPark sample notebook every day at midnight UTC, use the following command:

```shell
$ run-notebook schedule --at "cron(0 0 * * ? *)" --name "daily-spark-job" spark-test.ipynb -p input="s3://mybucket/myfile.txt" --image emr-notebook-runner --emr LivyTestCluster
```
