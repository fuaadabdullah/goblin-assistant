'use client';

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { PieChartConfig } from './types';
import { getChartPaletteColor } from '@/components/cost/chartPalette';

interface AllocationPieProps {
  title: string;
  data: Record<string, unknown>[];
  config: PieChartConfig;
}

const AllocationPie = ({ title, data, config }: AllocationPieProps) => {
  return (
    <div className="my-3 rounded-xl border border-border bg-surface/70 p-4 shadow-card">
      <h3 className="text-sm font-semibold text-text mb-3">{title}</h3>
      <ResponsiveContainer width="100%" height={280}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={90}
            label={({ name, value }) =>
              `${name}: ${typeof value === 'number' ? value.toFixed(1) : value}${config.valueLabel ? ` ${config.valueLabel}` : ''}`
            }
            labelLine={{ stroke: 'var(--muted)' }}
          >
            {data.map((_, i) => (
              <Cell key={`cell-${i}`} fill={getChartPaletteColor(i)} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: '8px',
              fontSize: '12px',
            }}
          />
          <Legend wrapperStyle={{ fontSize: '11px' }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

export default AllocationPie;
