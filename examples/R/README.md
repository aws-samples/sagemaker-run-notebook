# Running R notebooks

This example shows how to run a notebook written in R using the notebook scheduler.

### Build a container

To run in R, you need to build a container using the standard [R notebook container][1] published by Project Jupyter. One wrinkle here is that because Papermill defaults to using a Python kernel, you need to specify the kernel to use. The default R notebook uses the kernel `ir`. Putting these together, we can build the container using the CLI like this:

```shell
$ run-notebook create-container --base jupyter/r-notebook -k ir r-notebook-runner
```

[1]: https://github.com/jupyter/docker-stacks/tree/master/r-notebook

### Adding custom libraries

If you want to use libraries from CRAN or another repositories, you can include a shell script to install them in the container when it's being built. For example, to install ggplot2 and dplyr, your script could have the following line:

```shell
Rscript -e 'install.packages(c("ggplot2", "dplyr"), repos="https://cloud.r-project.org")'
```

If you save this script as `install.sh`, create the container like this:

```shell
$ run-notebook create-container --base jupyter/r-notebook -k ir --script install.sh r-notebook-runner
```

You can just use the [build-container.sh](build-container.sh) script which has the above command in it.

### Run the notebook

Now you can run the notebook in the normal way by asking for the r-notebook-runner image. From the CLI, it looks like this:

```shell
$ run-notebook run --image r-notebook-runner ggplot-sample.ipynb
```

From the JupyterLab extension, you can just open your R notebook and use `r-notebook-runner` as the image.
