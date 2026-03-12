'use client';

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
import type { BarChartConfig } from './types';
import { getChartPaletteColor } from '@/components/cost/chartPalette';

interface FinanceBarChartProps {
  title: string;
  data: Record<string, unknown>[];
  config: BarChartConfig;
}

const FinanceBarChart = ({ title, data, config }: FinanceBarChartProps) => {
  return (
    <div className="my-3 rounded-xl border border-border bg-surface/70 p-4 shadow-card">
      <h3 className="text-sm font-semibold text-text mb-3">{title}</h3>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(248, 240, 232, 0.1)" />
          <XAxis
            dataKey={config.xKey}
            stroke="rgba(248, 240, 232, 0.5)"
            fontSize={11}
            tickLine={false}
          />
          <YAxis stroke="rgba(248, 240, 232, 0.5)" fontSize={11} tickLine={false} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          {config.bars.length > 1 && <Legend wrapperStyle={{ fontSize: '11px' }} />}
          {config.bars.map((bar, i) => (
            <Bar
              key={bar.dataKey}
              dataKey={bar.dataKey}
              name={bar.label}
              fill={getChartPaletteColor(i)}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default FinanceBarChart;
