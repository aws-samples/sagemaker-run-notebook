#!/bin/bash

mkdir -p container

cd container

(cd ../../../container/; tar cf - .) | tar xf -

cp ../requirements.txt .

./build_and_push.sh weather-runner
