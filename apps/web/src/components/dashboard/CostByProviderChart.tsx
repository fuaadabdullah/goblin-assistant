'use client';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import type { ModelUsageRollup } from '../../types/api';
import { formatCost } from '@/utils/format-cost';
import { getChartPaletteColor } from '../cost/chartPalette';

function groupByCost(rows: ModelUsageRollup[]) {
  const map = new Map<string, number>();
  for (const row of rows) {
    map.set(row.provider, (map.get(row.provider) ?? 0) + row.total_cost_usd);
  }
  return Array.from(map.entries())
    .map(([provider, cost]) => ({ provider: provider.charAt(0).toUpperCase() + provider.slice(1), cost }))
    .sort((a, b) => b.cost - a.cost);
}

export const CostByProviderChart = ({ rows }: { rows: ModelUsageRollup[] }) => {
  const data = groupByCost(rows);
  if (data.length === 0) {
    return <div className="flex items-center justify-center h-40 text-sm text-muted">No cost data yet.</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
        <XAxis dataKey="provider" tick={{ fontSize: 10, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={(v: unknown) => formatCost(Number(v), { mode: 'summary' })} tick={{ fontSize: 10, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} width={44} />
        <Tooltip
          contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12 }}
          formatter={(v: unknown) => [formatCost(Number(v), { mode: 'summary' }), 'Cost']}
        />
        <Bar dataKey="cost" radius={[4, 4, 0, 0]}>
          {data.map((entry, index) => (
            <Cell key={entry.provider} fill={getChartPaletteColor(index)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};
