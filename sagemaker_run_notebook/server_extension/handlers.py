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
Module with all the individual handlers, which call boto commands and return the results to the frontend.
"""
import asyncio
import datetime
import io
import json
from json.decoder import JSONDecodeError
import os
from pathlib import Path
from urllib.parse import urlparse

import boto3
import botocore.exceptions
import sagemaker_run_notebook as run

from notebook.utils import url_path_join as ujoin, url2path
from notebook.base.handlers import APIHandler


def convert_times(o):
    if isinstance(o, datetime.datetime) or isinstance(o, datetime.timedelta):
        return o.__str__()
    else:
        raise TypeError("Object of type {} is not JSON serializable".format(type(o)))


import time


class BaseHandler(APIHandler):
    """
    Top-level parent class.
    """

    session = boto3.session.Session()

    @property
    def scheduler(self):
        return self.settings["scheduler"]

    def check_json(self):
        """Check to see if the incoming POST data is in JSON encoded format, cause that's all we understand.

        If it is in another format, write a 400 back to the client and return False, indicating that the
        handler method should return immediately. Otherwise, return True.
        """
        if self.request.headers["Content-Type"] != "application/json":
            self.set_status(
                400,
                "Bad Content-Type header: value: '{}'".format(
                    self.request.headers["Content-Type"]
                ),
            )
            self.set_header("Content-Type", "text/plain")
            self.finish("This server only accepts POST requests in 'application/json'")
            return False
        else:
            return True

    def required_params(self, params, required):
        """Check the incoming POST parameters to make sure that all the required parameters are included.

        Args:
          params (dict): The dictionary of params that was POSTed.
          required (list): A list of parameters that must be present in the params

        Returns:
          True, if all the required parameters are present and processing can continue.
          False, if there are missing paramters. Processing should return right away, the HTTP response is written already
        """
        for param in required:
            if param not in params:
                self.set_status(400, "Missing parameter: '{}'".format(param))
                self.set_header("Content-Type", "text/plain")
                self.finish(
                    "The parameter '{}' must be supplied with this POST request".format(
                        param
                    )
                )
                return False
        return True

    def load_params(self, required):
        """Loads the parameters to the POST request, checking for errors.
        The request must have the Content-Type 'application/json', be a well-formatted JSON object, and
        contain all the keys included in the required list.

        Args:
          required (list): The list of keys that must be inluded in the input for it to be valid.

        Returns:
          A dict object with the POSTed parameters if the are valid and None otherwise. If None is returned, processings
          the request should stop, the HTTP response has already been written.
        """
        if not self.check_json():
            return None

        try:
            data = json.loads(self.request.body.decode("utf-8"))

            if not self.required_params(data, ["image", "input_path", "notebook"]):
                return None
            else:
                return data
        except JSONDecodeError as e:
            self.set_status(400, "Improperly formatted JSON POST data")
            self.set_header("Content-Type", "text/plain")
            self.finish("JSON parser error: '{}'".format(str(e)))
            return False

    def json_response(self, response):
        """Take an object and return it to the client as a JSON formatted response"""
        self.set_header("Content-Type", "application/json")
        self.finish(json.dumps(response, default=convert_times))

    def error_response(self, http_status, type, message):
        """Construct a JSON bad request error and return it to the client"""
        self.set_header("Content-Type", "application/json")
        self.set_status(http_status)
        self.finish(json.dumps(dict(error=dict(type=type, message=message))))

    def client_error_response(self, client_error):
        """Construct the error response when we get a boto ClientError"""
        http_status = client_error.response.get("HTTPStatusCode", 400)
        message = client_error.response.get("Error", {}).get("Message", "Unknown error")
        self.error_response(http_status, "ClientError", message)

    def botocore_error_response(self, core_error):
        """Construct the error response when we get a boto CoreError"""
        http_status = 400
        message = str(core_error)
        self.error_response(http_status, "BotoCoreError", message)


class RunsHandler(BaseHandler):
    _tracker = None

    @classmethod
    def setTracker(cls, tracker):
        cls._tracker = tracker

    @property
    def tracker(self):
        if self._tracker is None:
            self.setTracker(run.NotebookRunTracker(session=self.session, log=self.log))
        return self._tracker

    async def get(self):
        """
        Handler for listing the notebook runs.
        """
        try:
            await self.tracker.update()
            runs = list(self.tracker)
            self.json_response({"runs": runs})
        except botocore.exceptions.ClientError as e:
            self.client_error_response(e)
        except botocore.exceptions.BotoCoreError as e:
            self.botocore_error_response(e)


class RunHandler(BaseHandler):
    def get(self, job_name):
        try:
            desc = run.describe_run(job_name, session=self.session)
            self.json_response({"run": desc})
        except botocore.exceptions.ClientError as e:
            self.client_error_response(e)
        except botocore.exceptions.BotoCoreError as e:
            self.botocore_error_response(e)

    def delete(self, job_name):
        try:
            run.stop_run(job_name, session=self.session)
            self.finish()
        except botocore.exceptions.ClientError as e:
            self.client_error_response(e)
        except botocore.exceptions.BotoCoreError as e:
            self.botocore_error_response(e)


class OutputHandler(BaseHandler):
    def get(self, job_name):
        try:
            d = run.describe_run(job_name, session=self.session)

            s3obj = d["Result"]
            o = urlparse(s3obj)
            bucket = o.netloc
            key = o.path[1:]

            s3 = self.session.resource("s3")
            obj = s3.Object(bucket, key)  # pylint: disable=no-member
            data = obj.get()["Body"].read().decode("utf-8")

            response = dict(notebook=d["Notebook"], output_object=s3obj, data=data)

            self.json_response(response)
        except botocore.exceptions.ClientError as e:
            self.client_error_response(e)
        except botocore.exceptions.BotoCoreError as e:
            self.botocore_error_response(e)


class RulesHandler(BaseHandler):
    async def get(self):
        """Handler for listing the schedules"""
        try:
            schedules = []
            generator = run.describe_schedules(n=20, session=self.session)
            for schedule in generator:
                self.log.debug(f'Described rule: {schedule["name"]}')
                await asyncio.sleep(0)
                schedules.append(schedule)
            self.json_response({"schedules": schedules})
        except botocore.exceptions.ClientError as e:
            self.client_error_response(e)
        except botocore.exceptions.BotoCoreError as e:
            self.botocore_error_response(e)


class RuleHandler(BaseHandler):
    def get(self, rule_name):
        """Get information on a specific schedule"""
        try:
            schedule = run.describe_schedule(rule_name)
            self.json_response({"schedules": [schedule]})
        except botocore.exceptions.ClientError as e:
            self.client_error_response(e)
        except botocore.exceptions.BotoCoreError as e:
            self.botocore_error_response(e)

    def post(self, rule_name):
        data = self.load_params(["image", "input_path", "notebook"])
        if data is None:
            return

        params = data.get("parameters", {})
        if isinstance(params, str):
            params = json.loads(params)

        kwargs = dict(
            rule_name=rule_name,
            image=data["image"],
            input_path=data["input_path"],
            output_prefix=data.get("output_prefix", None),
            notebook=data["notebook"],
            parameters=params,
            role=data.get("role", None),
            schedule=data.get("schedule", None),
            event_pattern=data.get("event_pattern", None),
        )
        instance_type = data.get("instance_type", None)
        if instance_type:
            kwargs["instance_type"] = instance_type

        try:
            run.schedule(**kwargs)
            self.json_response(dict(rule_name=rule_name))
        except botocore.exceptions.ClientError as e:
            self.client_error_response(e)
        except botocore.exceptions.BotoCoreError as e:
            self.botocore_error_response(e)

    def delete(self, rule_name):
        """Delete a rule"""
        try:
            run.unschedule(rule_name=rule_name)
            self.finish()
        except botocore.exceptions.ClientError as e:
            self.client_error_response(e)
        except botocore.exceptions.BotoCoreError as e:
            self.botocore_error_response(e)


class InvokeHandler(BaseHandler):
    def post(self):
        data = self.load_params(["image", "input_path", "notebook"])
        if data is None:
            return

        params = data.get("parameters", {})
        if isinstance(params, str):
            params = json.loads(params)

        kwargs = dict(
            image=data["image"],
            input_path=data["input_path"],
            output_prefix=data.get("output_prefix", None),
            notebook=data["notebook"],
            parameters=params,
            role=data.get("role", None),
        )
        instance_type = data.get("instance_type", None)
        if instance_type:
            kwargs["instance_type"] = instance_type

        try:
            job_name = run.invoke(**kwargs)
            self.json_response(dict(job_name=job_name))
        except botocore.exceptions.ClientError as e:
            self.client_error_response(e)
        except botocore.exceptions.BotoCoreError as e:
            self.botocore_error_response(e)
        except run.InvokeException as ie:
            self.error_response(
                400, "InvokeException", f"Lambda function returned error: {str(ie)}"
            )
        except ValueError as ve:
            self.error_response(400, "ValueError", str(ve))


class UploadHandler(BaseHandler):
    def put(self):
        try:
            with io.BytesIO(self.request.body) as f:
                s3object = run.upload_fileobj(f)
            self.json_response(dict(s3Object=s3object))
        except botocore.exceptions.ClientError as e:
            self.client_error_response(e)
        except botocore.exceptions.BotoCoreError as e:
            self.botocore_error_response(e)


def setup_handlers(web_app):
    """
    Setups all of the run command handlers.
    Every handler is defined here, to be used in scheduler.py file.
    """

    prefix = "/sagemaker-scheduler/"
    run_handlers = [
        ("runs", RunsHandler),
        ("run/(.+)", RunHandler),
        ("run", InvokeHandler),
        ("schedules", RulesHandler),
        ("schedule/(.+)", RuleHandler),
        ("upload", UploadHandler),
        ("output/(.+)", OutputHandler),
    ]

    # add the baseurl to our paths
    base_url = web_app.settings["base_url"]
    run_handlers = [(ujoin(base_url, prefix, x[0]), x[1]) for x in run_handlers]

    web_app.add_handlers(".*", run_handlers)
