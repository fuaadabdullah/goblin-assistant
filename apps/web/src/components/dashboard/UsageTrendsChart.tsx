'use client';

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { ModelUsageRollup } from '../../types/api';

interface DayPoint { date: string; tokens: number; requests: number }

function groupByDate(rows: ModelUsageRollup[]): DayPoint[] {
  const map = new Map<string, DayPoint>();
  for (const row of rows) {
    const p = map.get(row.usage_date) ?? { date: row.usage_date, tokens: 0, requests: 0 };
    p.tokens += row.total_tokens;
    p.requests += row.request_count;
    map.set(row.usage_date, p);
  }
  return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date)).slice(-30);
}

function shortDate(iso: string): string {
  const parts = iso.split('-');
  return `${parts[1]}/${parts[2]}`;
}

function fmtTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

export const UsageTrendsChart = ({ rows }: { rows: ModelUsageRollup[] }) => {
  const data = groupByDate(rows);
  if (data.length === 0) {
    return <div className="flex items-center justify-center h-40 text-sm text-muted">No usage data yet.</div>;
  }
  return (
    <ResponsiveContainer width="100%" height={180}>
      <AreaChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="tokenGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.25} />
            <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" vertical={false} />
        <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fontSize: 10, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={fmtTokens} tick={{ fontSize: 10, fill: 'var(--color-muted)' }} axisLine={false} tickLine={false} width={36} />
        <Tooltip
          contentStyle={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12 }}
          labelFormatter={(label: unknown) => shortDate(String(label))}
          formatter={(v: unknown) => [fmtTokens(Number(v)), 'Tokens']}
        />
        <Area type="monotone" dataKey="tokens" stroke="var(--color-primary)" strokeWidth={2} fill="url(#tokenGrad)" dot={false} activeDot={{ r: 3 }} />
      </AreaChart>
    </ResponsiveContainer>
  );
};
