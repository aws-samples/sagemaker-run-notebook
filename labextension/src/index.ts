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

import { ILayoutRestorer, JupyterFrontEnd, JupyterFrontEndPlugin, ILabShell } from '@jupyterlab/application';

import { ICommandPalette, MainAreaWidget, WidgetTracker } from '@jupyterlab/apputils';
import { IStateDB } from '@jupyterlab/coreutils';

import { IIconRegistry } from '@jupyterlab/ui-components';
import { IRenderMimeRegistry } from '@jupyterlab/rendermime';

import { RunsWidget } from './widgets/RunsWidget';
import { RulesWidget } from './widgets/RulesWidget';
import { ScheduleWidget } from './widgets/ScheduleWidget';
import { RunsModel } from './models/RunsModel';
import registerSharingIcons from './style/icons';
import { RulesModel } from './models/RulesModel';

function activate(
  app: JupyterFrontEnd,
  shell: ILabShell,
  palette: ICommandPalette,
  restorer: ILayoutRestorer,
  iconRegistry: IIconRegistry,
  rendermime: IRenderMimeRegistry,
  stateDB: IStateDB,
) {
  console.log('JupyterLab extension sagemaker_run_notebook is activated!');

  let runsWidget: MainAreaWidget<RunsWidget>;
  let rulesWidget: MainAreaWidget<RulesWidget>;
  const runsModel = new RunsModel();
  const rulesModel = new RulesModel();

  registerSharingIcons(iconRegistry);

  const tracker = new WidgetTracker<MainAreaWidget<RunsWidget>>({
    namespace: 'sagemaker_run_notebooks',
  });
  // Track and restore the widget state
  const tracker1 = new WidgetTracker<MainAreaWidget<RulesWidget>>({
    namespace: 'sagemaker_run_notebooks_schedules',
  });

  // Add the list runs command
  const command = 'sagemaker_run_notebook:open_list_runs';
  app.commands.addCommand(command, {
    label: 'List Notebook Runs',
    execute: () => {
      if (!runsWidget) {
        const content = new RunsWidget(app, rendermime, runsModel);
        runsWidget = new MainAreaWidget({ content });
        runsWidget.id = 'sagemaker_run_notebook_list_runs';
        runsWidget.title.iconClass = 'scheduler-tab-icon fa fa-rocket';
        runsWidget.title.label = 'Notebook Runs';
        runsWidget.title.closable = true;
        runsWidget.disposed.connect(() => {
          runsWidget = undefined;
        });
      }
      if (!tracker.has(runsWidget)) {
        // Track the state of the widget for later restoration
        tracker.add(runsWidget);
      }
      if (!runsWidget.isAttached) {
        // Attach the widget to the main work area if it's not there
        app.shell.add(runsWidget, 'main');
      }
      // refresh the list on the widget
      runsWidget.content.update();

      // Activate the widget
      app.shell.activateById(runsWidget.id);
    },
  });

  // Add the command to the palette.
  palette.addItem({ command, category: 'SageMaker Run Notebook' });

  const command1 = 'sagemaker_run_notebook:open_list_schedules';
  app.commands.addCommand(command1, {
    label: 'List Notebook Schedules',
    execute: () => {
      if (!rulesWidget) {
        const content = new RulesWidget(rulesModel);
        rulesWidget = new MainAreaWidget({ content });
        rulesWidget.id = 'sagemaker_run_notebook_list_schedules';
        rulesWidget.title.iconClass = 'scheduler-tab-icon fa fa-rocket';
        rulesWidget.title.label = 'Notebook Schedules';
        rulesWidget.title.closable = true;
        rulesWidget.disposed.connect(() => {
          rulesWidget = undefined;
        });
      }

      if (!tracker1.has(rulesWidget)) {
        // Track the state of the widget for later restoration
        tracker1.add(rulesWidget);
      }
      if (!rulesWidget.isAttached) {
        // Attach the widget to the main work area if it's not there
        app.shell.add(rulesWidget, 'main');
      }
      // refresh the list on the widget
      rulesWidget.content.update();

      // Activate the widget
      app.shell.activateById(rulesWidget.id);
    },
  });

  // Add the command to the palette.
  palette.addItem({ command: command1, category: 'SageMaker Run Notebook' });

  // Create the schedule widget sidebar
  const scheduleWidget = new ScheduleWidget(app, shell, runsModel, rulesModel, stateDB);
  scheduleWidget.id = 'jp-schedule';
  scheduleWidget.title.iconClass = 'jp-SideBar-tabIcon fa fa-rocket fa-2x scheduler-sidebar-icon';
  scheduleWidget.title.caption = 'Schedule';

  // Let the application restorer track the running panel for restoration of
  // application state (e.g. setting the running panel as the current side bar
  // widget).
  restorer.add(scheduleWidget, 'schedule-sidebar');

  // Rank has been chosen somewhat arbitrarily to give priority to the running
  // sessions widget in the sidebar.
  app.shell.add(scheduleWidget, 'left', { rank: 200 });

  // Track and restore the widget states
  restorer.restore(tracker, {
    command,
    name: () => 'sagemaker_run_notebooks',
  });
  restorer.restore(tracker1, {
    command: command1,
    name: () => 'sagemaker_run_notebooks_schedules',
  });
}

/**
 * Initialization data for the sagemaker_run_notebook extension.
 */
const extension: JupyterFrontEndPlugin<void> = {
  id: 'sagemaker_run_notebook',
  autoStart: true,
  requires: [ILabShell, ICommandPalette, ILayoutRestorer, IIconRegistry, IRenderMimeRegistry, IStateDB],
  activate: activate,
};

export default extension;
