'use client';

import type { TableConfig } from './types';

interface ProjectionsTableProps {
  title: string;
  data: Record<string, unknown>[];
  config: TableConfig;
}

const ProjectionsTable = ({ title, data, config }: ProjectionsTableProps) => {
  const { columns, highlight } = config;

  return (
    <div className="my-3 rounded-xl border border-border bg-surface/70 p-4 shadow-card">
      <h3 className="text-sm font-semibold text-text mb-3">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="border border-border bg-surface-hover px-3 py-1.5 text-left font-semibold text-text text-xs"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIdx) => {
              const isHighlighted =
                highlight &&
                highlight.value !== undefined &&
                row[highlight.key] === highlight.value;

              return (
                <tr
                  key={rowIdx}
                  className={isHighlighted ? 'bg-primary/10' : ''}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className="border border-border px-3 py-1.5 text-xs text-text align-top"
                    >
                      {String(row[col.key] ?? '—')}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ProjectionsTable;
