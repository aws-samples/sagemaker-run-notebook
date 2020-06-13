/* Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License"). You
 * may not use this file except in compliance with the License. A copy of
 * the License is located at
 *
 *     http://aws.amazon.com/apache2.0/
 *
 * or in the "license" file accompanying this file. This file is
 * distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
 * ANY KIND, either express or implied. See the License for the specific
 * language governing permissions and limitations under the License.
 */

/**
 * The shapes for the interaction with the RESTful Jupyter server extension that backs
 * the notebook runner
 */

export interface Run {
  Notebook: string;
  Rule: string;
  Parameters: string;
  Job: string;
  Status: string;
  Failure: string;
  Created: string;
  Start: string;
  End: string;
  Elapsed: string;
  Result: string;
  Input: string;
  Image: string;
  Instance: string;
  Role: string;
}

export interface ErrorInfo {
  type: string;
  message: string;
}

export interface ErrorResponse {
  error: ErrorInfo;
}

export interface ListRunsResponse {
  runs: Run[];
}

export interface RunResponse {
  run: Run;
}

export interface Rule {
  name: string;
  notebook: string;
  parameters: any; // eslint-disable-line  @typescript-eslint/no-explicit-any
  schedule: string;
  event_pattern: string;
  image: string;
  instance: string;
  role: string;
  state: string;
  input_path: string;
  output_prefix: string;
}

export interface ListRulesResponse {
  schedules: Rule[];
}

export interface CreateRuleRequest {
  image: string;
  input_path: string;
  output_prefix?: string;
  notebook: string;
  parameters: any; // eslint-disable-line  @typescript-eslint/no-explicit-any
  role: string;
  schedule?: string;
  event_pattern?: string;
  instance_type?: string;
}

export interface CreateRuleResponse {
  rule_name: string;
}

export interface OutputNotebook {
  notebook: string;
  output_object: string;
  data: any; // eslint-disable-line  @typescript-eslint/no-explicit-any
}

export interface UploadNotebookResponse {
  s3Object: string;
}

export interface InvokeRequest {
  image: string;
  input_path: string;
  output_prefix?: string;
  notebook: string;
  parameters?: any; // eslint-disable-line  @typescript-eslint/no-explicit-any
  role?: string;
  instance_type?: string;
}

export interface InvokeResponse {
  job_name: string;
}
