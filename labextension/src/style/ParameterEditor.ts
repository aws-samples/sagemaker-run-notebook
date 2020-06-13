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

import { style } from 'typestyle';

export const parameterEditorTableClass = style({
  textAlign: 'left',
  marginLeft: '8px',
  $nest: {
    '& th': {
      fontWeight: 400,
    },
  },
});

export const parameterEditorNoParametersClass = style({
  fontStyle: 'italic',
  padding: '4px 0px 6px 0px',
});

export const parameterEditorAddItemClass = style({
  marginLeft: '4px',
  color: 'var(--jp-ui-font-color0)',
  backgroundColor: 'var(--jp-layout-color0)',
  $nest: {
    '&:hover': {
      backgroundColor: 'var(--jp-layout-color3)',
    },
    '&:active': {
      color: 'var(--jp-ui-inverse-font-color0)',
      backgroundColor: 'var(--jp-inverse-layout-color3)',
    },
  },
});

export const closeIcon = style({
  backgroundSize: '16px',
  backgroundImage: 'var(--jp-icon-close)',
  height: '16px',
  width: '16px',
  padding: '4px 0px 4px 4px',
  backgroundPosition: 'center',
  backgroundRepeat: 'no-repeat',
  $nest: {
    '&:hover': {
      backgroundImage: 'var(--jp-icon-close-circle)',
    },
  },
});
