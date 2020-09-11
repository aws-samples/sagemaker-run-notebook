#!/bin/bash

# Build a container to run an R notebook. Edit install.sh to add any packages that you want to use.
run-notebook create-container --base jupyter/r-notebook -k ir --script install.sh r-notebook-runner