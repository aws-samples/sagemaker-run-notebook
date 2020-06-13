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

import {
  closeIcon,
  parameterEditorAddItemClass,
  parameterEditorNoParametersClass,
  parameterEditorTableClass,
} from '../style/ParameterEditor';
import { NotebookPanel } from '@jupyterlab/notebook';
import { IObservableJSON } from '@jupyterlab/observables';
import { JSONObject, JSONArray } from '@phosphor/coreutils';
import { ISignal } from '@phosphor/signaling';
import { SchedulePanel } from './SchedulePanel';

const METADATA_KEY = 'sagemaker_run_notebook';

export interface ParameterKV {
  name: string;
  value: any; // eslint-disable-line  @typescript-eslint/no-explicit-any
}

export interface ParameterEditorProps {
  onChange(parameterEditor: ParameterEditor): void;
  notebookPanel: NotebookPanel;
  notebookPanelChanged: ISignal<SchedulePanel, NotebookPanel>;
}

interface ParameterEditorState {
  parameters: ParameterKV[];
}

export type ParameterEntryErrors = Record<number, string>;
export interface ParameterErrors {
  nameErrors: ParameterEntryErrors;
  valueErrors: ParameterEntryErrors;
}

export class ParameterEditor extends React.Component<ParameterEditorProps, ParameterEditorState> {
  constructor(props: ParameterEditorProps) {
    super(props);
    this.notebookPanelChanged = props.notebookPanelChanged;
    this.currentNotebookPanel = props.notebookPanel;
    this.currentMetadata = null;
    this.onChange = props.onChange;
    this.state = { parameters: this.extractSavedParameters() };
    this.computeNewJSON(false);
    this.updateParameterTracker();
    this.notebookPanelChanged.connect(this.onNotebookPanelChanged, this);
  }

  componentWillUnmount() {
    this.notebookPanelChanged.disconnect(this.onNotebookPanelChanged, this);
  }

  private onNotebookPanelChanged(_: SchedulePanel, notebookPanel: NotebookPanel) {
    this.currentNotebookPanel = notebookPanel;
    this.getSavedParameters();
    this.updateParameterTracker();
  }

  private updateParameterTracker() {
    if (this.currentMetadata) {
      this.currentMetadata.changed.disconnect(this.getSavedParameters);
    }
    const panel = this.currentNotebookPanel;
    if (panel) {
      this.currentMetadata = panel.model.metadata;
      this.currentMetadata.changed.connect(this.getSavedParameters, this);
    }
  }

  private extractSavedParameters(): ParameterKV[] {
    let result: ParameterKV[] = [];
    const panel = this.currentNotebookPanel;
    if (panel) {
      const metadata = panel.model.metadata.get(METADATA_KEY) as JSONObject;
      const params = metadata && ((metadata['saved_parameters'] as unknown) as ParameterKV[]);
      if (params) {
        result = params;
      }
    }
    return result;
  }

  private getSavedParameters(): void {
    if (this.currentNotebookPanel) {
      this.setState({ parameters: this.extractSavedParameters() }, () => this.computeNewJSON(false));
    }
  }

  private setSavedParameters(): void {
    const panel = this.currentNotebookPanel;
    if (panel) {
      const metadata = (panel.model.metadata.get(METADATA_KEY) as JSONObject) || {};
      metadata['saved_parameters'] = (this.state.parameters as unknown) as JSONArray;
      panel.model.metadata.set(METADATA_KEY, metadata);
      panel.model.dirty = true; // metadata.set should do this, but doesn't
    }
  }

  render() {
    let block: JSX.Element;
    if (!this.state.parameters || this.state.parameters.length === 0) {
      block = (
        <p className={parameterEditorNoParametersClass}>
          No parameters defined. Press &ldquo;+&rdquo; to add parameters.
        </p>
      );
    } else {
      block = (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            {this.state.parameters.map((p, i) => (
              <tr key={`parameter-${i}`}>
                <td>
                  <input
                    type="text"
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => this.nameChanged(e, i)}
                    value={p.name}
                    title="Parameter"
                  />
                </td>
                <td>
                  <input
                    type="text"
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => this.valueChanged(e, i)}
                    value={p.value}
                    title="Value"
                  />
                </td>
                <td className={closeIcon} onClick={() => this.onMinusClick(i)}></td>
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    return (
      <div>
        <div>Parameters:</div>
        <div className={parameterEditorTableClass}>
          {block}
          <SmallButton onClick={this.onAddClick} label="+" tooltip="Add a parameter" />
        </div>
      </div>
    );
  }

  private onAddClick = (): void => {
    const params = this.state.parameters;
    params.push({ name: '', value: '' });
    this.setState({ parameters: params });
  };

  private onMinusClick = (i: number): void => {
    const params = this.state.parameters;
    params.splice(i, 1);
    this.setState({ parameters: params });
    this.computeNewJSON(true);
  };

  private nameChanged = (e: React.ChangeEvent<HTMLInputElement>, i: number): void => {
    const params = this.state.parameters;
    params[i].name = e.target.value;
    this.setState({ parameters: params }, () => this.computeNewJSON(true));
  };

  private valueChanged = (e: React.ChangeEvent<HTMLInputElement>, i: number): void => {
    const params = this.state.parameters;
    params[i].value = e.target.value;
    this.setState({ parameters: params }, () => this.computeNewJSON(true));
  };

  private computeNewJSON(updateMetadata: boolean): void {
    let valid = true;
    const seen: Set<string> = new Set<string>();
    const result: ParameterKV[] = [];
    const nameErrors: ParameterEntryErrors = {};
    const valueErrors: ParameterEntryErrors = {};

    this.state.parameters.forEach((element, idx) => {
      if (element.name.length === 0) {
        valid = false;
        nameErrors[idx] = 'Name must be specified';
      } else {
        if (element.name in seen) {
          valid = false;
          nameErrors[idx] = 'Duplicate parameter';
        } else {
          let val = element.value;
          // this mostly exists to let folks pass numbers as numbers, but in theory they can pass any JSON through.
          try {
            val = JSON.parse(val);
          } catch (SyntaxError) {} // eslint-disable-line  no-empty
          result.push({ name: element.name, value: val });
          seen.add(element.name);
        }
      }
    });
    this.parametersObject = valid ? result : null;
    this.nameErrors = nameErrors;
    this.valueErrors = valueErrors;
    this.onChange(this);
    if (updateMetadata) {
      this.setSavedParameters();
    }
  }

  get value(): ParameterKV[] {
    return this.parametersObject;
  }

  get errors(): ParameterErrors {
    return { nameErrors: this.nameErrors, valueErrors: this.valueErrors };
  }

  private onChange: (parameterEditor: ParameterEditor) => void;

  // The object representation (that will be returned to the caller)
  private notebookPanelChanged: ISignal<SchedulePanel, NotebookPanel>;
  private currentNotebookPanel: NotebookPanel;
  private currentMetadata: IObservableJSON;
  private parametersObject: ParameterKV[];
  private nameErrors: ParameterEntryErrors;
  private valueErrors: ParameterEntryErrors;
}

interface SmallButtonProps {
  label: string;
  tooltip: string;
  onClick(event: React.MouseEvent<HTMLInputElement>): void;
}

function SmallButton(props: SmallButtonProps) {
  return (
    <input
      type="button"
      className={parameterEditorAddItemClass}
      onClick={props.onClick}
      value={props.label}
      title={props.tooltip}
    />
  );
}
