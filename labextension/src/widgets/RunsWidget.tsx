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

import { ReactWidget } from '@jupyterlab/apputils';

import { RunList } from '../components/RunList';

import { RunsModel } from '../models/RunsModel';
import { JupyterFrontEnd } from '@jupyterlab/application';
import { IRenderMimeRegistry } from '@jupyterlab/rendermime';
import { scrollableWidgetClass } from '../style/Widget';
import { Message } from '@phosphor/messaging';

export class RunsWidget extends ReactWidget {
  /**
   * Construct a new widget for listing notebook runs
   */
  constructor(app: JupyterFrontEnd, rendermime: IRenderMimeRegistry, model: RunsModel) {
    super();
    this._app = app;
    this._rendermime = rendermime;
    this._model = model;
    this.addClass(scrollableWidgetClass);
  }

  processMessage(msg: Message): void {
    switch (msg.type) {
      case 'before-show':
        this._model.setActive(true);
        break;
      case 'before-hide':
        this._model.setActive(false);
        break;
    }
    super.processMessage(msg);
  }

  render() {
    return <RunList app={this._app} rendermime={this._rendermime} model={this._model} />;
  }

  private _model: RunsModel;
  private _app: JupyterFrontEnd;
  private _rendermime: IRenderMimeRegistry;
}
