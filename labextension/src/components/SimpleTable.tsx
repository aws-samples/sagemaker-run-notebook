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
import { tableClass, cellClass, tablePageClass, tablePageTitleClass, tableWrapperClass } from '../style/SimpleTable';

export interface SimpleTablePageProps {
  title?: string;
  children?: JSX.Element;
}
export class SimpleTableProps {
  headings: string[];
  rows: (string | JSX.Element)[][];
}

interface CellData {
  content: string | JSX.Element;
  header?: boolean;
}

export function SimpleTablePage(data: SimpleTablePageProps) {
  let title = null;
  if (data.title) {
    title = <div className={tablePageTitleClass}>{data.title}</div>;
  }
  return (
    <div className={tablePageClass}>
      {title}
      {data.children}
    </div>
  );
}

export class SimpleTable extends React.Component<SimpleTableProps, {}> {
  renderHeadingRow = (_cell: string, cellIndex: number) => {
    const { headings } = this.props;

    return <Cell key={`heading-${cellIndex}`} content={headings[cellIndex]} header={true} />;
  };

  renderRow = (row: (string | JSX.Element)[], rowIndex: number) => {
    return (
      <tr key={`row-${rowIndex}`}>
        {row.map((cell, cellIndex) => {
          return <Cell key={`${rowIndex}-${cellIndex}`} content={cell} />;
        })}
      </tr>
    );
  };

  render() {
    const { headings, rows } = this.props;

    this.renderHeadingRow = this.renderHeadingRow.bind(this);
    this.renderRow = this.renderRow.bind(this);

    const theadMarkup = <tr key="heading">{headings.map(this.renderHeadingRow)}</tr>;

    const tbodyMarkup = rows.map(this.renderRow);

    return (
      <div className={tableWrapperClass}>
        <table className={tableClass}>
          <thead>{theadMarkup}</thead>
          <tbody>{tbodyMarkup}</tbody>
        </table>
      </div>
    );
  }
}

function Cell(data: CellData) {
  const cellMarkup = data.header ? (
    <th className="${cellClass} Cell-header">{data.content}</th>
  ) : (
    <td className={cellClass}>{data.content}</td>
  );

  return cellMarkup;
}
