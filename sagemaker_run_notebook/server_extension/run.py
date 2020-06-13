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

"""
Module for doing the work of notebook scheduling, sending results back to the handlers
"""

import os
import boto3


class Scheduler:
    """
    A single parent class containing all of the scheduler operations.
    """

    def __init__(self, contents_manager):
        self.contents_manager = contents_manager
        self.root_dir = os.path.expanduser(contents_manager.root_dir)
