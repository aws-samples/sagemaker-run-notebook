ARG BASE_IMAGE=need_an_image
FROM $BASE_IMAGE

ENV JUPYTER_ENABLE_LAB yes
ENV PYTHONUNBUFFERED TRUE

# If there's no Python in the image, install it and make it the default. This lets us use base
# images like nvidia/cuda. Note that this incantation only works on Debian bases
RUN if which python; then echo Python already installed; else \
    echo Installing Python; \
    apt update && \
    apt install -y python3 python3-pip && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1 && \
    pip install --upgrade pip && \
    rm -rf /var/lib/apt/lists/*; fi
COPY requirements.txt /tmp/requirements.txt
RUN pip install papermill jupyter nteract-scrapbook boto3 requests && pip install -r /tmp/requirements.txt

ENV PYTHONUNBUFFERED=TRUE
ENV PATH="/opt/program:${PATH}"
ARG KERNEL
ENV PAPERMILL_KERNEL=$KERNEL

# Set up the program in the image
COPY run_notebook execute.py init-script.sh /opt/program/
RUN bash /opt/program/init-script.sh

ENTRYPOINT ["/bin/bash"]

# because there is a bug where you have to be root to access the directories
USER root

