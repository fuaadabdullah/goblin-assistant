import React from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import type { PieLabelRenderProps } from 'recharts';

interface ChartData {
  name: string;
  tasks: number;
  [key: string]: unknown;
}

interface ProviderUsageChartProps {
  data: ChartData[];
}

const colors = ['#7c3aed', '#10b981', '#f59e0b', '#ef4444', '#06b6d4', '#a78bfa'];

interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    [key: string]: unknown;
  }>;
}

const CustomTooltip = ({ active, payload }: TooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <div className="p-2 bg-slate-800 border border-slate-700 rounded-md shadow-lg">
        <p className="label text-sm text-slate-300">{`${payload[0].name}`}</p>
        <p className="intro text-sm text-white">{`Tasks: ${payload[0].value}`}</p>
      </div>
    );
  }
  return null;
};

const ProviderUsageChart: React.FC<ProviderUsageChartProps> = ({ data }) => {
  return (
    <>
      <h2 className="text-lg font-semibold mb-4 text-white">Provider Usage (Approximated)</h2>
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Tooltip content={<CustomTooltip />} />
          <Legend iconType="circle" />
          <Pie
            data={data}
            dataKey="tasks"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={80}
            labelLine={false}
            label={(props: PieLabelRenderProps) => {
              const safeName =
                typeof props.name === 'string'
                  ? props.name
                  : props.name != null
                    ? String(props.name)
                    : 'Unknown';
              const percent = props.percent ?? 0;
              return `${safeName} ${(percent * 100).toFixed(0)}%`;
            }}
          >
            {data.map((_entry, index) => (
              <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </>
  );
};

export default ProviderUsageChart;
