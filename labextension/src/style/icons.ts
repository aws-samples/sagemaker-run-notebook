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

import { IIconRegistry } from '@jupyterlab/ui-components';

import infoCircleSvg from '../../style/icons/info_circle.svg';

export const ICON_INFO_CIRCLE = 'sm-sharing-info-circle';

export default function registerSharingIcons(iconRegistry: IIconRegistry) {
  iconRegistry.addIcon({ name: ICON_INFO_CIRCLE, svg: infoCircleSvg });
}
