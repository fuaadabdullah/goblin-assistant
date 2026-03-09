import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
} from 'recharts';
import type { PieLabelRenderProps } from 'recharts';
import { getChartPaletteColor } from './chartPalette';
import { formatCost } from '@/utils/format-cost';

interface ChartData {
  name: string;
  value: number;
  [key: string]: unknown;
}

type ProviderUsageMetric = 'requests' | 'cost';

interface ProviderUsageChartProps {
  data: ChartData[];
  metric?: ProviderUsageMetric;
}

interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    name: string;
    value: number;
    [key: string]: unknown;
  }>;
}

const ProviderUsageTooltip = ({
  active,
  payload,
  metric,
}: TooltipProps & { metric: ProviderUsageMetric }) => {
  if (active && payload && payload.length) {
    const label = metric === 'requests' ? 'Requests' : 'Cost';
    const value = payload[0].value;
    return (
      <div className="rounded-md border border-border bg-surface p-2 text-text shadow-card">
        <p className="label text-sm text-muted">{`${payload[0].name}`}</p>
        <p className="intro text-sm text-text">
          {metric === 'requests' ? `${label}: ${value}` : `${label}: ${formatCost(value, { mode: 'summary' })}`}
        </p>
      </div>
    );
  }
  return null;
};

const ProviderUsageChart: React.FC<ProviderUsageChartProps> = ({
  data,
  metric = 'requests',
}) => {
  const title = metric === 'requests' ? 'Provider Requests' : 'Provider Costs';

  if (metric === 'cost') {
    return (
      <>
        <h2 className="mb-4 text-lg font-semibold text-text">{title}</h2>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={data} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(248, 240, 232, 0.1)" />
            <XAxis dataKey="name" stroke="rgba(248, 240, 232, 0.5)" fontSize={12} />
            <YAxis
              stroke="rgba(248, 240, 232, 0.5)"
              fontSize={12}
              tickFormatter={(value: number | string) =>
                formatCost(Number(value), { mode: 'summary' })
              }
            />
            <Tooltip content={<ProviderUsageTooltip metric={metric} />} />
            <Legend iconType="circle" />
            <Bar dataKey="value" name="Cost">
              {data.map((entry, index) => (
                <Cell key={`cost-cell-${entry.name}`} fill={getChartPaletteColor(index)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </>
    );
  }

  return (
    <>
      <h2 className="mb-4 text-lg font-semibold text-text">{title}</h2>
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Tooltip content={<ProviderUsageTooltip metric={metric} />} />
          <Legend iconType="circle" wrapperStyle={{ color: 'var(--text)' }} />
          <Pie
            data={data}
            dataKey="value"
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
            {data.map((entry, index) => (
              <Cell key={`cell-${entry.name}`} fill={getChartPaletteColor(index)} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    </>
  );
};

export default ProviderUsageChart;
