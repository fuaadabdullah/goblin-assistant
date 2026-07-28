import type { ModelUsageRollup } from '../../types/api';
import { formatCost } from '@/utils/format-cost';

interface ProviderSummary {
  provider: string;
  requestCount: number;
  totalCostUsd: number;
  avgLatencyMs: number;
  models: string[];
}

function groupByProvider(rows: ModelUsageRollup[]): ProviderSummary[] {
  const map = new Map<string, { requests: number; cost: number; latencyTotal: number; models: Set<string> }>();
  for (const row of rows) {
    const entry = map.get(row.provider) ?? { requests: 0, cost: 0, latencyTotal: 0, models: new Set() };
    entry.requests += row.request_count;
    entry.cost += row.total_cost_usd;
    entry.latencyTotal += row.total_latency_ms;
    entry.models.add(row.model);
    map.set(row.provider, entry);
  }
  return Array.from(map.entries())
    .map(([provider, e]) => ({
      provider,
      requestCount: e.requests,
      totalCostUsd: e.cost,
      avgLatencyMs: e.requests > 0 ? Math.round(e.latencyTotal / e.requests) : 0,
      models: Array.from(e.models).slice(0, 3),
    }))
    .sort((a, b) => b.requestCount - a.requestCount);
}

function latencyBadge(ms: number): { label: string; className: string } {
  if (ms < 1000) return { label: `${ms} ms`, className: 'text-success' };
  if (ms < 3000) return { label: `${ms} ms`, className: 'text-warning' };
  return { label: `${ms} ms`, className: 'text-error' };
}

interface ProviderStatusGridProps {
  rows: ModelUsageRollup[];
}

export const ProviderStatusGrid = ({ rows }: ProviderStatusGridProps) => {
  const providers = groupByProvider(rows);
  if (providers.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border px-4 py-6 text-center text-sm text-muted">
        No provider usage data yet.
      </div>
    );
  }
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
      {providers.map((p) => {
        const latency = latencyBadge(p.avgLatencyMs);
        return (
          <div key={p.provider} className="rounded-xl border border-border bg-surface px-4 py-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-text capitalize">{p.provider}</span>
              <span className={`text-xs font-mono ${latency.className}`}>{latency.label}</span>
            </div>
            <div className="flex gap-4 text-xs text-muted">
              <span>
                <span className="font-semibold text-text">{p.requestCount.toLocaleString()}</span> req
              </span>
              <span>
                <span className="font-semibold text-text">{formatCost(p.totalCostUsd, { mode: 'summary' })}</span>
              </span>
            </div>
            {p.models.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {p.models.map((m) => (
                  <span key={m} className="px-1.5 py-0.5 rounded-md bg-surface-hover text-[10px] font-mono text-muted border border-border/60">
                    {(m.split('/').pop() ?? m)}
                  </span>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
