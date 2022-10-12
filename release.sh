#!/bin/bash

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

# The steps of a release
# 
# 0. Before the release, you must add release info to the ChangeLog. Do not
#    commit it.
# 1. Check that we're ready to do a release
# 2. Edit all the files that have the release number included
# 3. Do a local build to make sure everything is copasetic
# 4. Commit and push these files along with the Changelog

# TODO: Not yet implemented
# 5. Create a new release on github and upload the built files

# For #5, you need to go to the GitHub UI and create the release.
# The contents of the release should be all the files in the directory
# manual_dist/

# Start by figuring out what version that we're on and what the next version will be.
# We always update minor versions now. This script will have to be extended to support
# major version and patch version increments.

tag=$(git describe --tags --abbrev=0 --match 'v[0-9][0-9.]*')
old_major=$(sed 's/v\([0-9]*\)\.\([0-9]*\)\..*$/\1/' <<< "$tag")
old_minor=$(sed 's/v\([0-9]*\)\.\([0-9]*\)\..*$/\2/' <<< "$tag")

echo "This version = ${tag}, major=${old_major}, minor=${old_minor}"

new_major=${old_major}
new_minor=$((${old_minor} + 1))
new_version="${new_major}.${new_minor}.0"
new_tag="v${new_version}"

echo "Next version = ${new_tag}, major=${new_major}, minor=${new_minor}"

# Check that we're ready to do a release
#
# Rules:
# a) Only Changelog should be uncommitted.
# b) Changelog should have been modified to include the new tag
# c) There should have been some actual commits since the last version

if [ "$(git status -uno --porcelain CHANGELOG.md )" == "" ]
then 
  echo "CHANGELOG.md must be edited with info about the release before doing the release."
  exit 1
fi

if [ "$(git status -uno --porcelain | grep -v CHANGELOG.md)" != "" ]
then 
  echo "Commit or stash all files (except CHANGELOG.md) before doing the release."
  exit 1
fi

git diff CHANGELOG.md | grep -q "^+## ${new_tag} "
if [ $? -ne 0 ]
then 
  echo "CHANGELOG.md doesn't have a section for version ${new_tag}"
  exit 1
fi

sha_head=$(git rev-list -n 1 HEAD)
sha_tag=$(git rev-list -n 1 tags/${tag})

if [ "${sha_head}" == "${sha_tag}" ]
then
  echo "There have been no commits since ${tag}. You need to have at least one commit to do a release."
#  exit 1
fi

# Edit the various files that need to be edited with the version number

vmatch=$(sed <<< "${tag}" "s/\\./\\\\./g" | sed 's/^v//')
for file in QuickStart.md build-dist-files.sh docs/source/conf.py scripts/lifecycle-config/notebook-instances/start.sh scripts/lifecycle-config/studio/install-run-notebook.sh
do
  sed -e "s/${vmatch}/${new_version}/g" -i "" ${file}
done

sed -i "" -e "s/^version_info *=.*$/version_info = (${new_major}, ${new_minor}, 0)/" sagemaker_run_notebook/server_extension/_version.py
sed -i "" -e 's/^\( *\"version": *"\)[^"]*\(".*$\)/\1'${new_version}'\2/'  labextension/package.json

# Build the release distribution
set -e
./build-dist-files.sh

# Stage commit and push
git add -u
git commit -m "Push version to ${new_tag} (with release.sh)"
git tag ${new_tag}
git push && git push origin tags/${new_tag}
