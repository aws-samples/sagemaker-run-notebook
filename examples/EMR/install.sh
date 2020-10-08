#!/bin/bash

EMR_MASTER_IP=NONE

apt update
apt install -y gcc libkrb5-dev curl
pip install sparkmagic

cd $(pip show sparkmagic | grep '^Location:' | sed 's/^[^ ]* //')
jupyter-kernelspec install sparkmagic/kernels/sparkkernel
jupyter-kernelspec install sparkmagic/kernels/pysparkkernel
jupyter-kernelspec install sparkmagic/kernels/sparkrkernel

jupyter nbextension enable --py --sys-prefix widgetsnbextension 

mkdir ~/.sparkmagic
cd ~/.sparkmagic

echo "Fetching Sparkmagic example config from GitHub..."
curl -O https://raw.githubusercontent.com/jupyter-incubator/sparkmagic/master/sparkmagic/example_config.json

echo "Replacing python executable with wrapper..."
mv /opt/program/execute.py /opt/program/execute-orig.py

cat > /opt/program/execute.py << EOF
#!/usr/bin/env python

import os
import subprocess

emr_envvar = "EMR_ADDRESS"

def change_emr_addr(emr_addr):
    subprocess.run(["sed", "-i", 's%"url": *"http:/[^:]*:8998"%"url": "http://{}:8998"%g'.format(emr_addr), "{}/.sparkmagic/config.json".format(os.getenv("HOME"))], check=True)
    print("Set EMR address to {}".format(emr_addr))

def wrapper():
    emr_addr = os.environ.get(emr_envvar)

    if emr_addr:
        change_emr_addr(emr_addr)

    return subprocess.run(["python", "/opt/program/execute-orig.py"])


if __name__ == "__main__":
    wrapper()
EOF

echo "Replacing EMR master node IP in Sparkmagic config..."
# autoviz doesn't save widget state correctly, so we have to turn it off
sed "s/localhost/$EMR_MASTER_IP/g" example_config.json | sed 's/"use_auto_viz": .*,/"use_auto_viz": false,/' > config.json
