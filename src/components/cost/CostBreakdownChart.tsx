import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { formatCost } from '@/utils/format-cost';

interface ChartData {
  name: string;
  value: number;
  color: string;
}

interface CostBreakdownChartProps {
  data: ChartData[];
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    value: number;
    [key: string]: unknown;
  }>;
  label?: string;
}

const CustomTooltip = ({ active, payload, label }: TooltipProps) => {
  if (active && payload && payload.length) {
    return (
      <div className="p-2 bg-slate-800 border border-slate-700 rounded-md shadow-lg">
        <p className="label text-sm text-slate-300">{`${label}`}</p>
        <p className="intro text-sm text-white">{`Cost: ${formatCost(payload[0].value, { mode: 'summary' })}`}</p>
      </div>
    );
  }

  return null;
};

const CostBreakdownChart: React.FC<CostBreakdownChartProps> = ({ data }) => {
  // Get colors from CSS variables for theme consistency
  const borderColor = getComputedStyle(document.documentElement).getPropertyValue('--border').trim();
  const textColor = getComputedStyle(document.documentElement).getPropertyValue('--text').trim();
  
  return (
    <>
      <h2 className="text-lg font-semibold mb-4 text-text">Cost Breakdown by Provider</h2>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(248, 240, 232, 0.1)" />
          <XAxis dataKey="name" stroke="rgba(248, 240, 232, 0.5)" fontSize={12} />
          <YAxis
            stroke="rgba(248, 240, 232, 0.5)"
            fontSize={12}
            tickFormatter={(value: number | string) => formatCost(Number(value), { mode: 'summary' })}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(212, 165, 116, 0.1)' }} />
          <Legend iconType="circle" />
          {data.map((entry, index) => (
            <Bar key={`bar-${index}`} dataKey="value" name={entry.name} fill={entry.color} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </>
  );
};

export default CostBreakdownChart;
