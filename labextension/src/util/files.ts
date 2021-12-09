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

import { JupyterFrontEnd } from '@jupyterlab/application';
import { PathExt } from '@jupyterlab/coreutils';

/**
 * Given a desired filename, this returns it if it does not conflict with any existing files. If
 * there is a conflict, this returns an incremented filename like Test_1.ipynb or Test_2.ipynb.
 */
export async function getUniqueFilename(app: JupyterFrontEnd, filename: string) {
  const basename = PathExt.basename(filename);
  const components = basename.split('.');
  const extension = components.pop();
  const stem = components.join('.');

  const fileExists = async (name: string) => {
    try {
      await app.serviceManager.contents.get(name);
      return true;
    } catch (e) {
      if (e.response && e.response.status === 404) {
        return false;
      }
      throw e;
    }
  };

  let count = 1;
  let newName = filename;
  while (await fileExists(newName)) {
    newName = `${stem}_${count++}${extension}`;
  }

  return newName;
}
