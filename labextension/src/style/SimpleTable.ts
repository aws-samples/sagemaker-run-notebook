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

export const tablePageClass = style({
  background: 'var(--jp-layout-color1)',
  padding: '1rem 3.2rem',
  color: 'var(--jp-content-font-color1)',
});

export const tablePageTitleClass = style({
  fontSize: '1.5em',
  fontWeight: 'bold',
  marginBottom: '0.5em',
});

export const tableWrapperClass = style({
  maxWidth: '100vw',
});

export const tableClass = style({
  borderSpacing: '0px',
  background: 'var(--jp-layout-color1)',
  color: 'var(--jp-content-font-color1)',
  boxShadow: '0 1px 0 0 rgba(22, 29, 37, 0.05)',
  width: '100%',
  $nest: {
    '& th': {
      textAlign: 'left',
    },
  },
});

export const cellClass = style({
  border: '1px solid var(--jp-border-color1)',
  padding: '4px',
  textAlign: 'left',
});
