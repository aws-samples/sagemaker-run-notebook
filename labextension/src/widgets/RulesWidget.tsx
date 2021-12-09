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

import { RulesList } from '../components/RuleList';
import { RulesModel } from '../models/RulesModel';
import { scrollableWidgetClass } from '../style/Widget';
import { Message } from '@lumino/messaging';

export class RulesWidget extends ReactWidget {
  /**
   * Construct a new widget for listing notebook schedules
   */
  constructor(model: RulesModel) {
    super();
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
    return <RulesList model={this._model} />;
  }

  private _model: RulesModel;
}
