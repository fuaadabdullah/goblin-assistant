import React from 'react';

interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    name?: string;
    dataKey?: string;
    value?: number | string;
    [key: string]: unknown;
  }>;
  label?: string | number;
}

const ChartTooltip: React.FC<TooltipProps> = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;

  const rows = payload.map((entry, rowIndex) => {
    const resolvedName = entry.name || entry.dataKey || label;
    const rowName =
      typeof resolvedName === 'string'
        ? resolvedName
        : resolvedName != null
          ? String(resolvedName)
          : `Series ${rowIndex + 1}`;

    return {
      key: rowName,
      name: rowName,
      value: entry.value,
    };
  });

  return (
    <div className="rounded border border-border bg-surface p-2 text-sm text-text shadow-card">
      {label !== undefined && <div className="font-medium mb-1">{label}</div>}
      {rows.map((row) => (
        <div key={row.key} className="flex justify-between gap-4">
          <div className="text-muted">{row.name}</div>
          <div className="font-semibold">{row.value}</div>
        </div>
      ))}
    </div>
  );
};

export default ChartTooltip;
