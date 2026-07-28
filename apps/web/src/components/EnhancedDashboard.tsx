import { useState, useEffect } from 'react';
import Link from 'next/link';
import { RefreshCw } from 'lucide-react';
import { DashboardSkeleton } from './LoadingSkeleton';
import { useDashboardData } from '../hooks/useDashboardData';
import { DashboardError } from './dashboard/DashboardError';
import { MetricTiles } from './dashboard/MetricTiles';
import { StatusCardsGrid } from './dashboard/StatusCardsGrid';
import { ProviderStatusGrid } from './dashboard/ProviderStatusGrid';
import { UsageTrendsChart } from './dashboard/UsageTrendsChart';
import { CostByProviderChart } from './dashboard/CostByProviderChart';
import { RecentActivityTable } from './dashboard/RecentActivityTable';

function SectionHeading({ title, action }: { title: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 mb-3">
      <h2 className="text-xs font-semibold uppercase tracking-widest text-muted/80">{title}</h2>
      {action}
    </div>
  );
}

export default function EnhancedDashboard() {
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const { dashboard, loading, error, refresh } = useDashboardData();

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(refresh, 30_000);
    return () => clearInterval(id);
  }, [autoRefresh, refresh]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await refresh();
    setRefreshing(false);
  };

  if (loading) return <DashboardSkeleton />;

  if (error && !dashboard) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg p-4">
        <DashboardError error={error} onRetry={handleRefresh} />
      </div>
    );
  }

  const modelUsage = dashboard?.observability.modelUsage;
  const rows = modelUsage?.rows ?? [];
  const summary = modelUsage?.summary ?? null;
  const services = dashboard
    ? { api: dashboard.backend, chroma: dashboard.chroma, mcp: dashboard.mcp, rag: dashboard.rag, sandbox: dashboard.sandbox }
    : {};

  return (
    <div className="min-h-screen bg-bg py-6 px-4">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold text-text">Operations</h1>
            <p className="text-sm text-muted">Real-time system health and usage metrics</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setAutoRefresh((v) => !v)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                autoRefresh
                  ? 'bg-primary/10 border-primary/40 text-primary'
                  : 'border-border text-muted hover:border-border/80 hover:text-text'
              }`}
            >
              {autoRefresh ? '◉ Auto' : 'Auto'}
            </button>
            <button
              type="button"
              onClick={() => void handleRefresh()}
              disabled={refreshing}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-border text-muted hover:text-text hover:border-border/80 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3 h-3 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {error && dashboard && <DashboardError error={error} onRetry={handleRefresh} />}

        <MetricTiles summary={summary} services={services} />

        <div>
          <SectionHeading title="Service Health" />
          {dashboard && (
            <StatusCardsGrid
              backend={dashboard.backend}
              chroma={dashboard.chroma}
              mcp={dashboard.mcp}
              rag={dashboard.rag}
              sandbox={dashboard.sandbox}
            />
          )}
        </div>

        <div>
          <SectionHeading
            title="Providers"
            action={<Link href="/admin/providers" className="text-xs text-primary hover:underline">Manage →</Link>}
          />
          <ProviderStatusGrid rows={rows} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="rounded-xl border border-border bg-surface p-4">
            <SectionHeading title="Token Usage (30d)" />
            <UsageTrendsChart rows={rows} />
          </div>
          <div className="rounded-xl border border-border bg-surface p-4">
            <SectionHeading title="Cost by Provider" />
            <CostByProviderChart rows={rows} />
          </div>
        </div>

        <div className="rounded-xl border border-border bg-surface">
          <div className="px-4 pt-4 pb-1">
            <SectionHeading
              title="Recent Activity"
              action={<Link href="/admin/logs" className="text-xs text-primary hover:underline">View logs →</Link>}
            />
          </div>
          <RecentActivityTable rows={rows} limit={10} />
        </div>

        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border/40 text-xs text-muted">
          <span className="font-medium">Quick links:</span>
          {[
            { label: 'Chat', href: '/chat' },
            { label: 'Search', href: '/search' },
            { label: 'Sandbox', href: '/sandbox' },
            { label: 'Providers', href: '/admin/providers' },
            { label: 'Logs', href: '/admin/logs' },
            { label: 'Settings', href: '/settings' },
          ].map(({ label, href }) => (
            <Link key={href} href={href} className="hover:text-text hover:underline">{label}</Link>
          ))}
        </div>
      </div>
    </div>
  );
}
