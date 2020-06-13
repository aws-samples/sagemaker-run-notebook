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
import classnames from 'classnames';
import { JupyterFrontEnd } from '@jupyterlab/application';
import { Contents } from '@jupyterlab/services';
import { DefaultIconReact } from '@jupyterlab/ui-components';

import { testId } from '../util/testId';
import { getUniqueFilename } from '../util/files';
import { ICON_INFO_CIRCLE } from '../style/icons';
import { showRunDetails } from './RunDetailsDialog';

const messageClass = style({
  flex: '1 1 auto',
  whiteSpace: 'nowrap',
  overflow: 'hidden',
  marginRight: '12px',
});

const messageTitleClass = style({
  fontWeight: 'bold',
  marginBottom: '4px',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
});

const messageBodyClass = style({
  overflow: 'hidden',
  textOverflow: 'ellipsis',
});

const actionClass = style({
  flex: '0 0 auto',
  marginLeft: 'auto',
  display: 'flex',
});

const snapshotDetailsButtonClass = style({
  background: 'var(--jp-layout-color1)',
  color: 'var(--jp-ui-font-color1) !important',
  border: 'var(--jp-border-width) solid var(--jp-border-color1) !important',
  lineHeight: 'calc(32px - 2 * var(--jp-border-width)) !important',
  marginRight: '8px',
  $nest: {
    '&:hover': {
      background: 'var(--jp-layout-color2)',
      borderColor: 'var(--jp-border-color0)',
    },
    '&:active': {
      background: 'var(--jp-layout-color3)',
      borderColor: 'var(--jp-border-color2)',
    },
  },
});

const infoIconClass = style({
  marginRight: '12px',
  alignSelf: 'flex-start',
  $nest: {
    svg: {
      height: '24px',
      width: '24px',
      stroke: 'var(--jp-info-color2)',
    },
  },
});

interface ReadonlyNotebookHeaderProps {
  app: JupyterFrontEnd;
  document: Partial<Contents.IModel>;
  notebookName: string;
  jobName: string;
}

export const ReadonlyNotebookHeader: React.FC<ReadonlyNotebookHeaderProps> = ({ app, document, jobName }) => {
  /** Copies the file to the root JupyterLab directory with a unique filename, and opens it */
  const handleCopy = async () => {
    const { name } = document;
    const destinationPath = await getUniqueFilename(app, name);
    await app.serviceManager.contents.save(destinationPath, document);
    app.commands.execute('docmanager:open', { path: destinationPath });
  };

  return (
    <>
      <DefaultIconReact name={ICON_INFO_CIRCLE} className={infoIconClass} />
      <div className={messageClass}>
        <p className={messageTitleClass}>This is a read-only preview</p>
        <p className={messageBodyClass}>To run and edit the notebook, create a copy to your workspace.</p>
      </div>
      <div className={actionClass}>
        <button
          type="button"
          className={classnames('jp-mod-styled', snapshotDetailsButtonClass)}
          onClick={showRunDetails(jobName)}
          {...testId('snapshot-details-button')}
        >
          Execution details
        </button>
        <button type="button" className="jp-mod-styled jp-mod-accept" onClick={handleCopy} {...testId('copy-button')}>
          Create a copy
        </button>
      </div>
    </>
  );
};
