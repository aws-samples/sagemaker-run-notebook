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

export const sectionClass = style({
  marginTop: '8px',
  $nest: {
    '& header': {
      borderBottom: 'var(--jp-border-width) solid var(--jp-border-color2)',
      flex: '0 0 auto',
      fontSize: 'var(--jp-ui-font-size1)',
      fontWeight: 600,
      letterSpacing: '1px',
      margin: '0px 0px 8px 0px',
      padding: '8px 0px',
    },
  },
});

export const labeledRowClass = style({
  verticalAlign: 'top',
  $nest: {
    '&>*:last-child': {
      paddingLeft: '.6em',
    },
  },
});

export const kvContainer = style({
  display: 'grid',
  gridTemplateColumns: 'auto auto',
  gridGap: '.2em .6em',
});
