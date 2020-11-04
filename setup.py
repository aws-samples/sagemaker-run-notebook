"""Setup Module to setup Python serverextension for the sagemaker run notebook
extension. For non-dev installs, will also automatically
build (if package.json is present) and install (if the labextension exists,
eg the build succeeded) the corresponding labextension.
"""
import os
from pathlib import Path
from subprocess import CalledProcessError

from setupbase import (
    command_for_func,
    create_cmdclass,
    ensure_python,
    get_version,
    HERE,
    run,
)

import setuptools

# The name of the project
name = "sagemaker_run_notebook"

# Ensure a valid python version
ensure_python(">=3.5")

# Get our version
version = get_version(str(Path(HERE) / name / "server_extension" / "_version.py"))

lab_path = Path(HERE) / "labextension"

data_files_spec = [
    ("share/jupyter/lab/extensions", str(lab_path / name / "labextension"), "*.tgz"),
    (
        "etc/jupyter/jupyter_notebook_config.d",
        "sagemaker_run_notebook/server_extension/jupyter-config/jupyter_notebook_config.d",
        "sagemaker_run_notebook.json",
    ),
]


def runPackLabextension():
    if (lab_path / "package.json").is_file():
        try:
            run(["jlpm", "build:labextension"], cwd=str(lab_path))
        except CalledProcessError:
            pass


pack_labext = command_for_func(runPackLabextension)

cmdclass = create_cmdclass("pack_labext", data_files_spec=data_files_spec)
cmdclass["pack_labext"] = pack_labext
cmdclass.pop("develop")

with open("README.md", "r") as fh:
    long_description = fh.read()

required_packages = ["boto3>=1.10.44"]

setuptools.setup(
    name=name,
    version=version,
    author="Amazon Web Services",
    description="Schedule notebooks to run using SageMaker processing jobs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/awslabs/sagemaker-run-notebook",
    cmdclass=cmdclass,
    packages=["sagemaker_run_notebook", "sagemaker_run_notebook.server_extension"],
    license="Apache License 2.0",
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Framework :: Jupyter",
    ],
    python_requires=">=3.6",
    install_requires=required_packages,
    extras_require={
        "dev": [
            "python-minifier",
            "black",
            "pytest",
            "sphinx",
            "sphinx_rtd_theme",
            "autodocsumm",
            "sphinx-argparse",
            "jupyterlab~=1.2",
        ]
    },
    entry_points={
        "console_scripts": [
            "run-notebook=sagemaker_run_notebook.cli:main",
        ]
    },
    include_package_data=True,
    package_data={"sagemaker_run_notebook": ["cloudformation.yml", "container/**"]},
)
