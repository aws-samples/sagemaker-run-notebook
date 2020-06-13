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

import { RunsModel } from '../models/RunsModel';
import { NotebookPanel } from '@jupyterlab/notebook';
import { ServerConnection } from '@jupyterlab/services';
import { IStateDB, URLExt } from '@jupyterlab/coreutils';
import { JSONValue, ReadonlyJSONObject, JSONArray } from '@phosphor/coreutils';
import { Signal } from '@phosphor/signaling';
import { Widget } from '@phosphor/widgets';

import {
  UploadNotebookResponse,
  InvokeRequest,
  InvokeResponse,
  CreateRuleRequest,
  CreateRuleResponse,
  ErrorResponse,
} from '../server';
import { InputColumn, LabeledTextInput } from './InputColumn';
import { ParameterEditor, ParameterKV } from './ParameterEditor';
import { Alert, AlertProps } from './Alert';

import {
  runSidebarSectionClass,
  runSidebarNotebookNameClass,
  runSidebarNoHeaderClass,
  sidebarButtonClass,
  alertAreaClass,
  runSidebarNoNotebookClass,
  flexButtonsClass,
} from '../style/SchedulePanel';
import { JupyterFrontEnd, ILabShell } from '@jupyterlab/application';
import { RulesModel } from '../models/RulesModel';

const KEY = 'sagemaker-run-notebook:schedule-sidebar:data';

/** Interface for SchedulePanel component props */
export interface ISchedulePanelProps {
  app: JupyterFrontEnd;
  shell: ILabShell;
  runsModel: RunsModel;
  rulesModel: RulesModel;
  stateDB: IStateDB;
}

interface PersistentState {
  image: string;
  role: string;
  instanceType: string;
  ruleName: string;
  schedule: string;
  eventPattern: string;
}
interface ISchedulePanelState extends PersistentState {
  notebook: string;
  notebookPanel: NotebookPanel;
  parameters: ParameterKV[];
  alerts: (AlertProps & { key: string })[];
}

// convertParameters turns the parameters we use here into a map that the server and containter expect.
// TODO: fix the container to take lists and delete this function so that parameters are always in the order specified
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function convertParameters(params: ParameterKV[]): Record<string, any> {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const result: Record<string, any> = {};
  params.forEach((param) => {
    result[param.name] = param.value;
  });
  return result;
}

/** A React component for the schedule extension's main display */
export class SchedulePanel extends React.Component<ISchedulePanelProps, ISchedulePanelState> {
  constructor(props: ISchedulePanelProps) {
    super(props);
    this.app = props.app;
    this.shell = props.shell;
    this.currentNotebookChanged = new Signal<SchedulePanel, NotebookPanel>(this);
    this.setCurrentWidget(this.shell.currentWidget);
    this.state = {
      notebook: this.notebook,
      notebookPanel: this.currentNotebookPanel,
      image: '',
      parameters: null,
      role: '',
      instanceType: '',
      ruleName: '',
      schedule: '',
      eventPattern: '',
      alerts: [],
    };

    this.loadState();
    this.shell.currentChanged.connect(this.onCurrentWidgetChanged, this);
  }

  //TODO: track notebook renames
  private onCurrentWidgetChanged(sender: ILabShell, args: ILabShell.IChangedArgs) {
    const newWidget = args.newValue;
    const label = newWidget && newWidget.title.label;
    console.log(`current widget changed to ${label}`);
    this.setCurrentWidget(newWidget);
    this.setState({ notebook: this.notebook, notebookPanel: this.currentNotebookPanel });
  }

  private setCurrentWidget(newWidget: Widget): void {
    const context = newWidget && (newWidget as NotebookPanel).context;
    const session = context && context.session;
    const isNotebook = session && session.type === 'notebook';
    if (isNotebook) {
      this.currentNotebookPanel = newWidget as NotebookPanel;
      this.notebook = session.name;
    } else {
      this.currentNotebookPanel = null;
      this.notebook = null;
    }
    this.currentNotebookChanged.emit(this.currentNotebookPanel);
  }

  /**
   * Renders the component.
   *
   * @returns React element
   */
  render = (): React.ReactElement => {
    const notebookIndependent = (
      <div>
        {this.renderViewButtons()}
        {this.renderCurrentNotebook()}
      </div>
    );
    const notebookDependent = this.currentNotebookPanel ? (
      <div>
        {this.renderRunParameters()}
        {this.renderScheduleParameters()}
        {this.renderExecuteButtons()}
        {this.renderAlerts()}
      </div>
    ) : (
      <p className={runSidebarNoNotebookClass}>Select or create a notebook to enable execution and scheduling.</p>
    );
    return (
      <div>
        {notebookIndependent}
        {notebookDependent}
      </div>
    );
  };

  private renderViewButtons() {
    return (
      <div className={runSidebarSectionClass}>
        <header>View</header>
        <div>
          <div className={flexButtonsClass}>
            <input
              className={sidebarButtonClass}
              type="button"
              title="View notebook runs"
              value="Runs"
              onClick={this.onRunListClick}
            />
            <input
              className={sidebarButtonClass}
              type="button"
              title="View notebook schedules"
              value="Schedules"
              onClick={this.onScheduleListClick}
            />
          </div>
        </div>
      </div>
    );
  }

  private renderCurrentNotebook() {
    const notebook = this.state.notebook;
    let notebookDisplay: React.ReactElement;
    if (notebook != null) {
      notebookDisplay = <span>{notebook}</span>;
    } else {
      notebookDisplay = <span>No notebook selected</span>;
    }

    return (
      <div className={runSidebarSectionClass}>
        <header>Current Notebook</header>
        <p className={runSidebarNotebookNameClass}>{notebookDisplay}</p>
      </div>
    );
  }

  private renderRunParameters() {
    return (
      <div className={runSidebarSectionClass}>
        <header>Notebook Execution</header>
        <ParameterEditor
          onChange={this.onParametersChange}
          notebookPanel={this.currentNotebookPanel}
          notebookPanelChanged={this.currentNotebookChanged}
        />
        <InputColumn>
          <LabeledTextInput
            label="Image:"
            value={this.state.image}
            title="ECR image to use"
            onChange={this.onImageChange}
          />
          <LabeledTextInput
            label="Role:"
            value={this.state.role}
            title="IAM role to use"
            onChange={this.onRoleChange}
          />
          <LabeledTextInput
            label="Instance:"
            value={this.state.instanceType}
            title="Instance type to run on"
            onChange={this.onInstanceTypeChange}
          />
        </InputColumn>
      </div>
    );
  }

  private renderScheduleParameters() {
    return (
      <div className={runSidebarSectionClass}>
        <header>Schedule Rule</header>
        <InputColumn>
          <LabeledTextInput
            label="Rule Name:"
            value={this.state.ruleName}
            title="A name for this schedule"
            onChange={this.onRuleNameChange}
          />
          <LabeledTextInput
            label="Schedule:"
            value={this.state.schedule}
            title="Schedule for the notebook run"
            onChange={this.onScheduleChange}
          />
          <LabeledTextInput
            label="Event Pattern:"
            value={this.state.eventPattern}
            title="Events to trigger the notebook run"
            onChange={this.onEventPatternChange}
          />
        </InputColumn>
      </div>
    );
  }

  private renderExecuteButtons() {
    return (
      <div className={`${runSidebarSectionClass} ${runSidebarNoHeaderClass}`}>
        <div>
          <div className={flexButtonsClass}>
            <input
              className={sidebarButtonClass}
              type="button"
              title="Run the notebook"
              value="Run Now"
              onClick={this.onRunClick}
            />
            <input
              className={sidebarButtonClass}
              type="button"
              title="Create schedule"
              value="Create Schedule"
              onClick={this.onScheduleClick}
            />
          </div>
        </div>
      </div>
    );
  }

  private renderAlerts() {
    return (
      <div className={alertAreaClass}>
        {this.state.alerts.map((alert) => (
          <Alert key={`alert-${alert.key}`} type={alert.type} message={alert.message} />
        ))}
      </div>
    );
  }

  private onParametersChange = (editor: ParameterEditor): void => {
    this.setState({ parameters: editor.value });
  };

  private onImageChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    this.setState({ image: event.target.value }, () => this.saveState());
  };

  private onRoleChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    this.setState({ role: event.target.value }, () => this.saveState());
  };

  private onInstanceTypeChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    this.setState({ instanceType: event.target.value }, () => this.saveState());
  };

  private onRuleNameChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    this.setState({ ruleName: event.target.value }, () => this.saveState());
  };

  private onScheduleChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    this.setState({ schedule: event.target.value }, () => this.saveState());
  };

  private onEventPatternChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    this.setState({ eventPattern: event.target.value }, () => this.saveState());
  };

  private onRunListClick = async (): Promise<void> => {
    this.app.commands.execute('sagemaker_run_notebook:open_list_runs');
  };

  private onScheduleListClick = async (): Promise<void> => {
    this.app.commands.execute('sagemaker_run_notebook:open_list_schedules');
  };

  private onRunClick = async (): Promise<void> => {
    console.log('Run!!!');
    this.clearAlerts();
    try {
      this.addAlert({
        type: 'notice',
        message: `Starting notebook run for "${this.state.notebook}"`,
      });
      const content = this.currentNotebookPanel.model.toJSON();
      const s3Object = await this.uploadNotebook(content);
      console.log(`notebook uploaded to ${s3Object}`);

      // TODO: clean up non-camel-case entries in the server requests
      /* eslint-disable @typescript-eslint/camelcase */
      const request: InvokeRequest = {
        image: this.state.image,
        input_path: s3Object,
        notebook: this.state.notebook,
        parameters: convertParameters(this.state.parameters),
        role: this.state.role,
        instance_type: this.state.instanceType,
      };
      /* eslint-enable @typescript-eslint/camelcase */

      const jobName = await this.invokeNotebook(request);
      this.addAlert({ message: `Started notebook run "${jobName}"` });
      console.log(`started job ${jobName}`);
      this.props.runsModel.refresh();
    } catch (e) {
      this.addAlert({
        type: 'error',
        message: `Error starting run for "${this.state.notebook}": ${e.message}`,
      });
    }
  };

  private onScheduleClick = async (): Promise<void> => {
    console.log('Create schedule!!!');
    this.clearAlerts();
    try {
      this.addAlert({
        type: 'notice',
        message: `Creating rule "${this.state.ruleName}"`,
      });
      const content = this.currentNotebookPanel.model.toJSON();
      const s3Object = await this.uploadNotebook(content);
      console.log(`notebook uploaded to ${s3Object}`);

      /* eslint-disable @typescript-eslint/camelcase */
      const request: CreateRuleRequest = {
        image: this.state.image,
        input_path: s3Object,
        notebook: this.state.notebook,
        parameters: convertParameters(this.state.parameters),
        role: this.state.role,
        instance_type: this.state.instanceType,
      };

      const schedule = this.state.schedule;
      if (schedule !== '') {
        request.schedule = schedule;
      }
      const eventPattern = this.state.eventPattern;
      if (eventPattern !== '') {
        request.event_pattern = eventPattern;
      }
      /* eslint-enable @typescript-eslint/camelcase */

      const ruleName = await this.createRule(this.state.ruleName, request);
      this.addAlert({ message: `Created rule "${ruleName}"` });
      console.log(`created rule ${ruleName}`);
      this.props.rulesModel.refresh();
    } catch (e) {
      this.addAlert({
        type: 'error',
        message: `Error creating rule "${this.state.ruleName}": ${e.message}`,
      });
    }
  };

  private async uploadNotebook(notebook: JSONValue): Promise<string> {
    const settings = ServerConnection.makeSettings();
    const response = await ServerConnection.makeRequest(
      URLExt.join(settings.baseUrl, 'sagemaker-scheduler', 'upload'),
      { method: 'PUT', body: JSON.stringify(notebook) },
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
      throw Error('Uploading notebook to S3 failed: ' + errorMessage);
    }

    const data = (await response.json()) as UploadNotebookResponse;
    return data.s3Object;
  }

  // Figure out if the current notebook has a parameter cell marked
  private hasParameterCell(): boolean {
    if (!this.currentNotebookPanel) {
      return false;
    }
    const cells = this.currentNotebookPanel.model.cells;
    for (let i = 0; i < cells.length; i++) {
      const tags = cells.get(i).metadata.get('tags') as JSONArray;
      if (tags && tags.includes('parameters')) {
        return true;
      }
    }
    return false;
  }

  private runReady(): string[] {
    const result: string[] = [];
    if (!this.state.image) {
      result.push('missing container image');
    }
    if (!this.state.instanceType) {
      result.push('missing instance type');
    }
    if (this.state.parameters.length > 0 && !this.hasParameterCell()) {
      result.push(`no parameter cell defined in ${this.notebook}`);
    }
    return result;
  }

  private async invokeNotebook(request: InvokeRequest): Promise<string> {
    const errors = this.runReady();
    if (errors.length > 0) {
      throw new Error(errors.join(', '));
    }
    const settings = ServerConnection.makeSettings();
    const response = await ServerConnection.makeRequest(
      URLExt.join(settings.baseUrl, 'sagemaker-scheduler', 'run'),
      { method: 'POST', body: JSON.stringify(request) },
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
      throw Error(errorMessage);
    }

    const data = (await response.json()) as InvokeResponse;
    return data.job_name;
  }

  // Return an array of reasons that we can't create a schedule.
  private scheduleReady(): string[] {
    const result = this.runReady();
    if (!this.state.ruleName) {
      result.push('missing schedule name');
    }
    if (!(this.state.schedule || this.state.eventPattern)) {
      result.push('must have either a schedule or an event pattern');
    }
    return result;
  }

  private async createRule(ruleName: string, request: CreateRuleRequest): Promise<string> {
    const errors = this.scheduleReady();
    if (errors.length > 0) {
      throw new Error(errors.join(', '));
    }
    const settings = ServerConnection.makeSettings();
    const response = await ServerConnection.makeRequest(
      URLExt.join(settings.baseUrl, 'sagemaker-scheduler', 'schedule', ruleName),
      { method: 'POST', body: JSON.stringify(request) },
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
      throw Error(errorMessage);
    }

    const data = (await response.json()) as CreateRuleResponse;
    return data.rule_name;
  }

  private alertKey = 0;
  private addAlert(alert: AlertProps) {
    const key = this.alertKey++;

    const keyedAlert: AlertProps & { key: string } = { ...alert, key: `alert-${key}` };
    this.setState({ alerts: [keyedAlert] });
  }

  private clearAlerts() {
    this.setState({ alerts: [] });
  }

  private saveState() {
    const state = {
      image: this.state.image,
      role: this.state.role,
      instanceType: this.state.instanceType,
      ruleName: this.state.ruleName,
      schedule: this.state.schedule,
      eventPattern: this.state.eventPattern,
    };

    this.props.stateDB.save(KEY, state);
  }

  private loadState() {
    this.props.stateDB.fetch(KEY).then((s) => {
      const state = s as ReadonlyJSONObject;
      if (state) {
        this.setState({
          image: state['image'] as string,
          role: state['role'] as string,
          instanceType: state['instanceType'] as string,
          ruleName: state['ruleName'] as string,
          schedule: state['schedule'] as string,
          eventPattern: state['eventPattern'] as string,
        });
      }
    });
  }

  private app: JupyterFrontEnd;
  private shell: ILabShell;

  private currentNotebookPanel: NotebookPanel;
  private notebook: string;
  private currentNotebookChanged: Signal<SchedulePanel, NotebookPanel>;
}
