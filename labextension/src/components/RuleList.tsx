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

import { ServerConnection } from '@jupyterlab/services';
import { URLExt } from '@jupyterlab/coreutils';

import { RulesModel, RulesUpdate } from '../models/RulesModel';
import { Rule, ErrorResponse } from '../server';
import { SimpleTable, SimpleTablePage } from './SimpleTable';
import { tableLinkClass, tableEmptyClass } from '../style/tables';
import { showDialog, Dialog } from '@jupyterlab/apputils';

export interface RuleListProps {
  model: RulesModel;
}

interface RuleListState {
  rules: Rule[];
  error: string;
}

const Headers = ['Name', 'Notebook', 'Parameters', 'Schedule', 'Event', 'Image', 'Instance', 'Role', 'State', ''];

export class RulesList extends React.Component<RuleListProps, RuleListState> {
  constructor(props: RuleListProps) {
    super(props);
    this.state = { rules: props.model.rules, error: null };

    props.model.rulesChanged.connect(this.onRulesChanged, this);
  }

  private onRulesChanged(_: RulesModel, ruleInfo: RulesUpdate): void {
    this.setState({ rules: ruleInfo.rules, error: ruleInfo.error });
  }

  componentWillUnmount() {
    this.props.model.rulesChanged.disconnect(this.onRulesChanged, this);
  }

  private extractRow = (rule: Rule): (string | JSX.Element)[] => {
    return [
      rule.name,
      rule.notebook,
      this.formatParameters(rule.parameters),
      rule.schedule,
      rule.event_pattern,
      rule.image,
      rule.instance,
      rule.role,
      rule.state,
      <a key={rule.name} onClick={this.deleteRule(rule.name)} className={tableLinkClass}>
        Delete
      </a>,
    ];
  };

  // eslint-disable-next-line  @typescript-eslint/no-explicit-any
  private formatParameters(params: Record<string, any>) {
    return (
      <div>
        {Object.entries(params).map(([k, v]) => (
          <p key={`param-${k}`}>{`${k}: ${JSON.stringify(v)}`}</p>
        ))}
      </div>
    );
  }

  render() {
    let content: JSX.Element;
    if (this.state.rules) {
      // sometimes it seems that render gets called before the constructor ???
      const rows = this.state.rules.map(this.extractRow);
      if (rows.length === 0) {
        content = <div className={tableEmptyClass}>No schedules defined</div>;
      } else {
        content = <SimpleTable headings={Headers} rows={rows} />;
      }
    } else if (this.state.error) {
      content = <div className={tableEmptyClass}>Error retrieving rules: {this.state.error}</div>;
    } else {
      content = <div className={tableEmptyClass}>Loading rules...</div>;
    }
    return <SimpleTablePage title="Schedule and Event Rules">{content}</SimpleTablePage>;
  }

  private deleteRule(rule: string) {
    return async (): Promise<boolean> => {
      const deleteBtn = Dialog.warnButton({ label: 'Delete' });
      const result = await showDialog({
        title: 'Delete Rule?',
        body: `Do you want to delete the rule ${rule}?`,
        buttons: [Dialog.cancelButton(), deleteBtn],
      });

      if (result.button.accept) {
        console.log(`deleting rule ${rule}`);
        const settings = ServerConnection.makeSettings();
        const response = await ServerConnection.makeRequest(
          URLExt.join(settings.baseUrl, 'sagemaker-scheduler', 'schedule', rule),
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
            title: 'Error deleting schedule',
            body: <p>{errorMessage}</p>,
            buttons: [Dialog.okButton({ label: 'Close' })],
          });
          return;
        }
        this.props.model.refresh();
        return true;
      }
      return false;
    };
  }
}
