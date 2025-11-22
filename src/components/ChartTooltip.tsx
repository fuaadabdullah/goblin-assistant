import React from "react";

interface TooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string | number;
}

const ChartTooltip: React.FC<TooltipProps> = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;

  const rows = payload.map((p) => ({ name: p.name || p.dataKey || label, value: p.value }));

  return (
    <div className="bg-slate-800 text-slate-100 p-2 rounded shadow-md text-sm">
      {label !== undefined && <div className="font-medium mb-1">{label}</div>}
      {rows.map((r, i) => (
        <div key={i} className="flex justify-between gap-4">
          <div className="text-slate-300">{r.name}</div>
          <div className="font-semibold">{r.value}</div>
        </div>
      ))}
    </div>
  );
};

export default ChartTooltip;
