import type { ModelUsageRollupSummary } from '../../types/api';
import type { ServiceStatus } from '../../hooks/useDashboardData';
import { formatCost } from '@/utils/format-cost';
import { Activity, DollarSign, Zap, CheckCircle } from 'lucide-react';

interface MetricTilesProps {
  summary: ModelUsageRollupSummary | null;
  services: Record<string, ServiceStatus>;
}

function Tile({
  label,
  value,
  sub,
  icon: Icon,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ComponentType<{ className?: string }>;
  tone: 'neutral' | 'success' | 'warn' | 'error';
}) {
  const iconColor = {
    neutral: 'text-muted',
    success: 'text-success',
    warn: 'text-warning',
    error: 'text-error',
  }[tone];

  return (
    <div className="flex flex-col gap-1 rounded-xl border border-border bg-surface px-4 py-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-widest text-muted">
          {label}
        </span>
        <Icon className={`w-3.5 h-3.5 ${iconColor}`} />
      </div>
      <p className="text-xl font-semibold text-text leading-none">{value}</p>
      {sub && <p className="text-[11px] text-muted">{sub}</p>}
    </div>
  );
}

export const MetricTiles = ({ summary, services }: MetricTilesProps) => {
  const serviceList = Object.values(services);
  const healthyCount = serviceList.filter((s) => s.status === 'healthy').length;
  const totalCount = serviceList.length;
  const allHealthy = healthyCount === totalCount && totalCount > 0;
  const anyDown = serviceList.some((s) => s.status === 'unhealthy');

  const avgLatencyMs =
    summary && summary.request_count > 0
      ? Math.round(summary.total_latency_ms / summary.request_count)
      : null;

  const latencyTone: 'success' | 'warn' | 'error' | 'neutral' =
    avgLatencyMs === null
      ? 'neutral'
      : avgLatencyMs < 1000
        ? 'success'
        : avgLatencyMs < 3000
          ? 'warn'
          : 'error';

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <Tile
        label="Requests"
        value={summary ? summary.request_count.toLocaleString() : '—'}
        sub="all time"
        icon={Activity}
        tone="neutral"
      />
      <Tile
        label="Total cost"
        value={summary ? formatCost(summary.total_cost_usd, { mode: 'summary' }) : '—'}
        sub="all time"
        icon={DollarSign}
        tone="neutral"
      />
      <Tile
        label="Avg latency"
        value={avgLatencyMs !== null ? `${avgLatencyMs} ms` : '—'}
        sub="per request"
        icon={Zap}
        tone={latencyTone}
      />
      <Tile
        label="Services"
        value={totalCount > 0 ? `${healthyCount}/${totalCount}` : '—'}
        sub={anyDown ? 'degraded' : allHealthy ? 'all healthy' : 'checking…'}
        icon={CheckCircle}
        tone={anyDown ? 'error' : allHealthy ? 'success' : 'neutral'}
      />
    </div>
  );
};
