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

import React from 'react';
import { style } from 'typestyle';
import { StaticNotebook, NotebookModel } from '@jupyterlab/notebook';
import { MainAreaWidget, ReactWidget } from '@jupyterlab/apputils';
import { editorServices } from '@jupyterlab/codemirror';
import { JupyterFrontEnd } from '@jupyterlab/application';
import { IRenderMimeRegistry } from '@jupyterlab/rendermime';

import { ReadonlyNotebookHeader } from '../components/ReadonlyNotebookHeader';

const toolbarClass = style({
  minHeight: '88px !important',
  display: 'flex',
  padding: '20px',
  paddingRight: '28px',
  background: 'var(--jp-info-color3)',
  borderBottomColor: 'var(--jp-info-color2)',
  color: 'var(--ui-font-color1)',
  fontSize: 'var(--jp-ui-font-size1)',
  fontFamily: 'var(--jp-ui-font-family)',
});

// Override toolbar item style
const headerClass = style({
  flex: '1 !important',
  alignItems: 'center',
  padding: 0,
  lineHeight: 'unset !important',
  fontSize: 'var(--jp-ui-font-size2) !important',
});

/**
 * Our model is a subset of the `Contents.IModel` from Jupyter.
 */
interface RunListNotebookModel {
  name: string;
  content: any; // eslint-disable-line  @typescript-eslint/no-explicit-any
}

export function openReadonlyNotebook(
  app: JupyterFrontEnd,
  rendermime: IRenderMimeRegistry,
  document: RunListNotebookModel,
  notebookName: string,
  jobName: string,
) {
  const { name, content: nbContent } = document;

  const contentWidget = new StaticNotebook({
    rendermime,
    mimeTypeService: editorServices.mimeTypeService,
  });

  const widget = new MainAreaWidget({ content: contentWidget });
  widget.id = 'shared_notebook';
  widget.title.label = `[Read-only] ${name}`;
  widget.title.iconClass = 'notebook';
  widget.toolbar.addClass(toolbarClass);

  app.shell.add(widget, 'main');

  // Model must be populated after the widget is added.
  const nbModel = new NotebookModel();
  nbModel.mimeType = 'text/x-python';
  contentWidget.model = nbModel;

  nbModel.fromJSON(nbContent);
  contentWidget.widgets.forEach((cell) => {
    cell.readOnly = true;
  });

  const headerWidget = ReactWidget.create(
    <ReadonlyNotebookHeader app={app} document={document} notebookName={notebookName} jobName={jobName} />,
  );
  headerWidget.addClass(headerClass);

  widget.toolbar.addItem('header', headerWidget);

  return widget;
}
