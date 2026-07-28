import type { ModelUsageRollup } from '../../types/api';
import { formatCost } from '@/utils/format-cost';

function shortModel(model: string): string {
  const parts = model.split('/');
  return parts[parts.length - 1] ?? model;
}

export const RecentActivityTable = ({ rows, limit = 10 }: { rows: ModelUsageRollup[]; limit?: number }) => {
  const sorted = [...rows].sort((a, b) => b.usage_date.localeCompare(a.usage_date)).slice(0, limit);
  if (sorted.length === 0) {
    return <div className="px-4 py-6 text-sm text-muted text-center">No recent activity to show.</div>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border/60">
            {['Date', 'Provider', 'Model', 'Requests', 'Tokens', 'Cost', 'Avg latency'].map((h) => (
              <th key={h} className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-widest text-muted/70 first:pl-0 last:pr-0">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => {
            const avgMs = row.request_count > 0 ? Math.round(row.total_latency_ms / row.request_count) : 0;
            return (
              <tr key={`${row.usage_date}-${row.provider}-${row.model}-${i}`} className="border-b border-border/30 last:border-0 hover:bg-surface-hover/40 transition-colors">
                <td className="px-3 py-2 text-muted pl-0 font-mono">{row.usage_date}</td>
                <td className="px-3 py-2 text-text capitalize">{row.provider}</td>
                <td className="px-3 py-2 text-muted font-mono">{shortModel(row.model)}</td>
                <td className="px-3 py-2 text-text tabular-nums">{row.request_count.toLocaleString()}</td>
                <td className="px-3 py-2 text-text tabular-nums">{row.total_tokens.toLocaleString()}</td>
                <td className="px-3 py-2 text-text tabular-nums">{formatCost(row.total_cost_usd, { mode: 'summary' })}</td>
                <td className="px-3 py-2 text-muted tabular-nums pr-0">{avgMs} ms</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
