#!/bin/bash

# Install R packages into your container. Simply change the contents of the list to add more/different 
# packages. You can also add more shell commands here.
Rscript -e 'install.packages(c("ggplot2"), repos="https://cloud.r-project.org")'