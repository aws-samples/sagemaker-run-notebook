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

import * as React from 'react';

import { JupyterFrontEnd } from '@jupyterlab/application';
import { showDialog, Dialog } from '@jupyterlab/apputils';
import { IRenderMimeRegistry } from '@jupyterlab/rendermime';
import { ServerConnection } from '@jupyterlab/services';
import { URLExt } from '@jupyterlab/coreutils';

import { RunsModel, RunsUpdate } from '../models/RunsModel';
import { Run, OutputNotebook, ErrorResponse } from '../server';
import { SimpleTable, SimpleTablePage } from './SimpleTable';
import { tableLinkClass, tableEmptyClass } from '../style/tables';
import { openReadonlyNotebook } from '../widgets/ReadOnlyNotebook';
import { showRunDetails, processDate } from './RunDetailsDialog';

const basenamePattern = /([^/]*)$/;

function viewDetails(jobName: string): () => Promise<void> {
  return showRunDetails(jobName);
}

function openResult(jobName: string, app: JupyterFrontEnd, rendermime: IRenderMimeRegistry) {
  return async () => {
    const settings = ServerConnection.makeSettings();
    const response = await ServerConnection.makeRequest(
      URLExt.join(settings.baseUrl, 'sagemaker-scheduler', 'output', jobName),
      { method: 'GET' },
      settings,
    );

    if (!response.ok) {
      const error = (await response.json()) as ErrorResponse;
      let errorMessage: string;
      if (error.error) {
        errorMessage = error.error.message;
      } else {
        errorMessage = JSON.stringify(error);
      }
      showDialog({
        title: 'Error opening notebook',
        body: <p>{errorMessage}</p>,
        buttons: [Dialog.okButton({ label: 'Close' })],
      });
      return;
    }
    const info = (await response.json()) as OutputNotebook;
    const match = basenamePattern.exec(info.output_object);
    const outputName = match[1];
    const document = {
      name: outputName,
      content: JSON.parse(info.data),
    };
    openReadonlyNotebook(app, rendermime, document, outputName, jobName);
  };
}

function stopJob(jobName: string) {
  return async () => {
    console.log(`Stop job ${jobName}`);
    const settings = ServerConnection.makeSettings();
    const response = await ServerConnection.makeRequest(
      URLExt.join(settings.baseUrl, 'sagemaker-scheduler', 'run', jobName),
      { method: 'DELETE' },
      settings,
    );

    if (!response.ok) {
      const error = (await response.json()) as ErrorResponse;
      let errorMessage: string;
      if (error.error) {
        errorMessage = error.error.message;
      } else {
        errorMessage = JSON.stringify(error);
      }
      showDialog({
        title: 'Error stopping execution',
        body: <p>{errorMessage}</p>,
        buttons: [Dialog.okButton({ label: 'Close' })],
      });
      return;
    }
  };
}

export interface RunListProps {
  app: JupyterFrontEnd;
  rendermime: IRenderMimeRegistry;
  model: RunsModel;
}

interface RunListState {
  runs: Run[];
  error: string;
}

const Headers = ['Rule', 'Notebook', 'Parameters', 'Status', 'Start', 'Elapsed', '', ''];

export class RunList extends React.Component<RunListProps, RunListState> {
  constructor(props: RunListProps) {
    super(props);
    this.state = { runs: props.model.runs, error: null };
    this._app = props.app;
    this._rendermime = props.rendermime;

    props.model.runsChanged.connect(this.onRunsChanged, this);
  }

  private onRunsChanged(_: RunsModel, runInfo: RunsUpdate): void {
    this.setState({ runs: runInfo.runs, error: runInfo.error });
  }

  componentWillUnmount(): void {
    this.props.model.runsChanged.disconnect(this.onRunsChanged, this);
  }

  private extractRow = (run: Run): (string | JSX.Element)[] => {
    const app = this._app;
    const rendermime = this._rendermime;

    const details = (
      <a onClick={viewDetails(run.Job)} className={tableLinkClass}>
        View Details
      </a>
    );
    let links: JSX.Element = null;
    if (run.Status === 'Completed') {
      links = (
        <a onClick={openResult(run.Job, app, rendermime)} className={tableLinkClass}>
          View Output
        </a>
      );
    } else if (run.Status === 'InProgress') {
      links = (
        <a onClick={stopJob(run.Job)} className={tableLinkClass}>
          Stop Run
        </a>
      );
    }
    return [
      run.Rule,
      run.Notebook,
      this.formatParameters(run.Parameters),
      run.Status,
      processDate(run.Start, run.Status),
      run.Elapsed,
      details,
      links,
    ];
  };

  private formatParameters(params: string) {
    try {
      // eslint-disable-next-line  @typescript-eslint/no-explicit-any
      const parsed = JSON.parse(params) as Record<string, any>;
      return (
        <div>
          {Object.entries(parsed).map(([k, v]) => (
            <p key={`param-${k}`}>{`${k}: ${JSON.stringify(v)}`}</p>
          ))}
        </div>
      );
    } catch (SyntaxError) {
      return params;
    }
  }

  render(): JSX.Element {
    let content: JSX.Element;
    if (this.state.runs) {
      // sometimes it seems that render gets called before the constructor ???
      const rows = this.state.runs.map(this.extractRow);
      if (rows.length === 0) {
        content = <div className={tableEmptyClass}>No notebooks have been run</div>;
      } else {
        content = <SimpleTable headings={Headers} rows={rows} />;
      }
    } else if (this.state.error) {
      content = <div className={tableEmptyClass}>Error retrieving execution history: {this.state.error}</div>;
    } else {
      content = <div className={tableEmptyClass}>Loading execution history...</div>;
    }
    return <SimpleTablePage title="Notebook Execution History">{content}</SimpleTablePage>;
  }

  private _app: JupyterFrontEnd;
  private _rendermime: IRenderMimeRegistry;
}
