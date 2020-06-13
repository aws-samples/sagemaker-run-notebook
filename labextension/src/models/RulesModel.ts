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

import { ServerConnection } from '@jupyterlab/services';
import { Poll, URLExt } from '@jupyterlab/coreutils';

import { IDisposable } from '@phosphor/disposable';
import { ISignal, Signal } from '@phosphor/signaling';

import { ListRulesResponse, Rule, ErrorResponse } from '../server';

export interface RulesUpdate {
  rules: Rule[] | null;
  error: string;
}

export class RulesModel implements IDisposable {
  constructor() {
    this._refreshing = false;
    this._active = false;

    const interval = 30 * 1000; // TODO: make this a setting

    const poll = new Poll({
      factory: () => this.refresh(),
      frequency: {
        interval: interval,
        backoff: true,
        max: 300 * 1000,
      },
      standby: 'when-hidden',
    });
    this._poll = poll;
  }

  setActive(active: boolean): void {
    this._active = active;
    if (active) {
      this.refresh();
    }
  }

  async refresh(): Promise<void> {
    this.getRules().then((result: RulesUpdate) => {
      if (result) {
        this._rules = result.rules;
        this._rulesChanged.emit(result);
      }
    });
  }

  private async getRules(): Promise<RulesUpdate> {
    if (this._active && !this._refreshing) {
      this._refreshing = true;
      try {
        const settings = ServerConnection.makeSettings();
        const response = await ServerConnection.makeRequest(
          URLExt.join(settings.baseUrl, 'sagemaker-scheduler', 'schedules'),
          { method: 'GET' },
          settings,
        );

        if (!response.ok) {
          const error = (await response.json()) as ErrorResponse;
          return { rules: null, error: error.error.message };
        }

        const data = (await response.json()) as ListRulesResponse;
        return { rules: data.schedules, error: null };
      } finally {
        this._refreshing = false;
      }
    }
  }

  get rules(): Rule[] {
    return this._rules;
  }

  /**
   * A signal emitted when the current list of runs changes.
   */
  get rulesChanged(): ISignal<RulesModel, RulesUpdate> {
    return this._rulesChanged;
  }

  /**
   * Get whether the model is disposed.
   */
  get isDisposed(): boolean {
    return this._isDisposed;
  }

  /**
   * Dispose of the resources held by the model.
   */
  dispose(): void {
    if (this.isDisposed) {
      return;
    }
    this._isDisposed = true;
    if (this._poll) {
      this._poll.dispose();
    }
    Signal.clearData(this);
  }

  private _rules: Rule[];
  private _isDisposed = false;
  private _rulesChanged = new Signal<RulesModel, RulesUpdate>(this);

  private _poll: Poll;
  private _refreshing: boolean;
  private _active: boolean;
}
