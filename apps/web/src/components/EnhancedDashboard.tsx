import { useState, useEffect } from 'react';
import Link from 'next/link';
import { DashboardSkeleton } from './LoadingSkeleton';
import { useDashboardData } from '../hooks/useDashboardData';
import { DashboardHeader } from './dashboard/DashboardHeader';
import { CostOverviewBanner } from './dashboard/CostOverviewBanner';
import { StatusCardsGrid } from './dashboard/StatusCardsGrid';
import { DashboardError } from './dashboard/DashboardError';
import { Grid } from './ui';

/**
 * Global Health Dashboard
 * Comprehensive monitoring with expandable cards, sparklines, and error tracking
 * Refactored into smaller, focused components for better maintainability
 */
export default function EnhancedDashboard() {
  const [autoRefresh, setAutoRefresh] = useState(false);
  const { dashboard, loading, error, refresh } = useDashboardData();

  // Auto-refresh every 30 seconds if enabled
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh, refresh]);

  if (loading) {
    return <DashboardSkeleton />;
  }

  if (error && !dashboard) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg p-4">
        <DashboardError error={error} onRetry={refresh} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg py-6 px-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <DashboardHeader
          onRefresh={refresh}
          autoRefresh={autoRefresh}
          onToggleAutoRefresh={() => setAutoRefresh(!autoRefresh)}
          loading={loading}
        />

        {/* Live region for status updates */}
        <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
          {dashboard &&
            `Dashboard updated. Services: ${Object.values(dashboard).filter((s): s is { status: string } => typeof s === 'object' && s !== null && 'status' in s && s.status === 'healthy').length} healthy`}
        </div>

        {/* Error banner (non-blocking) */}
        {error && dashboard && (
          <DashboardError error={error} onRetry={refresh} />
        )}

        {/* Cost Overview Banner */}
        {dashboard && (
          <CostOverviewBanner
            totalCost={dashboard.cost.total}
            todayCost={dashboard.cost.today}
            thisMonthCost={dashboard.cost.thisMonth}
            byProvider={dashboard.cost.byProvider}
          />
        )}

        {/* Health Cards Grid */}
        {dashboard && (
          <StatusCardsGrid
            backend={dashboard.backend}
            chroma={dashboard.chroma}
            mcp={dashboard.mcp}
            rag={dashboard.rag}
            sandbox={dashboard.sandbox}
          />
        )}

        {/* Start Here */}
        <div className="bg-surface rounded-xl border border-border p-6">
          <div className="flex items-center justify-between gap-4 flex-wrap mb-4">
            <div>
              <h2 className="text-lg font-semibold text-text">Start Here</h2>
              <p className="text-sm text-muted">
                Jump into chat, search your memory, or run a safe sandbox experiment.
              </p>
            </div>
            <Link
              href="/chat"
              className="px-4 py-2 rounded-lg bg-primary text-text-inverse font-medium shadow-glow-primary hover:brightness-110"
            >
              Ask a Question
            </Link>
          </div>
          <Grid gap="sm">
            <Link
              href="/chat"
              className="px-4 py-3 bg-primary text-text-inverse rounded-lg hover:brightness-110 shadow-glow-primary transition-all text-center font-medium block"
            >
              Ask Anything
              <span className="block text-xs text-text-inverse/80 mt-1">
                Decisions, summaries, and next steps from your context
              </span>
            </Link>
            <Link
              href="/search"
              className="px-4 py-3 bg-accent text-text-inverse rounded-lg hover:brightness-110 shadow-glow-accent transition-all text-center font-medium block"
            >
              Find a Document
              <span className="block text-xs text-text-inverse/80 mt-1">
                Search notes, policies, or saved answers
              </span>
            </Link>
            <Link
              href="/sandbox"
              className="px-4 py-3 bg-success text-text-inverse rounded-lg hover:brightness-110 transition-all text-center font-medium block"
            >
              Try a Code Example
              <span className="block text-xs text-text-inverse/80 mt-1">
                A safe place to test small snippets
              </span>
            </Link>
          </Grid>

          <div className="mt-6">
            <h3 className="text-sm font-semibold text-muted uppercase tracking-wide">
              Advanced Tools
            </h3>
            <Grid gap="sm">
            <Link
              href="/admin/providers"
              className="px-4 py-3 bg-primary/15 text-text border border-border rounded-lg hover:bg-primary/20 transition-all text-center font-medium block"
            >
              Connections
              <span className="block text-xs text-muted mt-1">
                Manage AI providers and keys
              </span>
            </Link>
            <Link
              href="/admin/logs"
              className="px-4 py-3 bg-surface-hover text-text border border-border rounded-lg hover:bg-surface-active transition-all text-center font-medium block"
            >
              Activity
                <span className="block text-xs text-muted mt-1">
                  Review system events and alerts
                </span>
              </Link>
            </Grid>
          </div>
        </div>
      </div>
    </div>
  );
}
