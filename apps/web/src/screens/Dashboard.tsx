import React from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Activity, BarChart3, Clock, Rocket } from 'lucide-react';
import CostBreakdownChart from '@/components/cost/CostBreakdownChart';
import ProviderUsageChart from '@/components/cost/ProviderUsageChart';
import { getChartPaletteColor } from '@/components/cost/chartPalette';
import { runtimeClient } from '@/lib/api/runtimeClient';
import { useSystemStatus } from '@/hooks/useSystemStatus';
import { TristateWrapper, Card } from '@/components/ui';
import StatCard from '@/components/StatCard';
import EmptyState from '@/components/ui/EmptyState';
import { useDashboardData } from '@/hooks/useDashboardData';

type DashboardPeriod = '7d' | '30d' | 'all';

interface DashboardActivityItem {
  id: string;
  kind: 'cost' | 'request' | 'status' | 'empty';
  title: string;
  description: string;
  timestampLabel: string;
  period: DashboardPeriod;
  tone?: 'success' | 'warning' | 'danger' | 'muted';
}

const DASHBOARD_PERIODS: Array<{ value: DashboardPeriod; label: string }> = [
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' },
  { value: 'all', label: 'All' },
];

const ONBOARDING_STORAGE_KEY = 'goblinos-onboarding-complete';

const formatProviderName = (provider: string) =>
  provider.replace(/[_-]+/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());

const statusTone = (state: string): DashboardActivityItem['tone'] => {
  if (state === 'ok') return 'success';
  if (state === 'degraded') return 'warning';
  if (state === 'down') return 'danger';
  return 'muted';
};

const activityDotClass = (tone: DashboardActivityItem['tone']) => {
  if (tone === 'success') return 'bg-success';
  if (tone === 'warning') return 'bg-warning';
  if (tone === 'danger') return 'bg-danger';
  return 'bg-muted';
};

const DashboardContent: React.FC = () => {
  const [period, setPeriod] = React.useState<DashboardPeriod>('7d');
  const [showOnboardingPrompt, setShowOnboardingPrompt] = React.useState(false);
  const {
    data: costSummary,
    isLoading: costLoading,
    error: costError,
  } = useQuery({
    queryKey: ['costSummary'],
    queryFn: () => runtimeClient.getCostSummary(),
  });

  const { status: systemStatus } = useSystemStatus();
  const { dashboard } = useDashboardData();

  React.useEffect(() => {
    try {
      setShowOnboardingPrompt(localStorage.getItem(ONBOARDING_STORAGE_KEY) !== 'true');
    } catch {
      setShowOnboardingPrompt(false);
    }
  }, []);

  const costData = React.useMemo(() => {
    if (!costSummary?.cost_by_provider) return [];
    return Object.entries(costSummary.cost_by_provider).map(([provider, cost], index) => ({
      name: provider,
      value: cost as number,
      color: getChartPaletteColor(index),
    }));
  }, [costSummary]);

  const usageData = React.useMemo(() => {
    const requestsByProvider = costSummary?.requests_by_provider;
    if (!requestsByProvider) return [];

    return Object.entries(requestsByProvider).map(([provider, requests]) => ({
      name: provider,
      value: requests as number,
    }));
  }, [costSummary]);

  const usageMetric = usageData.length > 0 ? 'requests' : 'cost';
  const usageFallbackData =
    usageMetric === 'requests' ? usageData : costData.map(({ name, value }) => ({ name, value }));

  const hasData = costData.length > 0 || usageData.length > 0;
  const totalCost = hasData ? (costSummary?.total_cost ?? dashboard.cost.total) : 0;
  const totalRequests =
    costSummary?.requests_by_provider && Object.keys(costSummary.requests_by_provider).length > 0
      ? Object.values(costSummary.requests_by_provider).reduce(
          (sum, requests) => sum + Number(requests || 0),
          0
        )
      : 0;
  const activeProviders = costData.length;

  const statusDot = (state: string) => {
    if (state === 'ok') return 'bg-success';
    if (state === 'degraded') return 'bg-warning';
    if (state === 'down') return 'bg-danger';
    return 'bg-muted';
  };

  const activityItems = React.useMemo<DashboardActivityItem[]>(() => {
    const items: DashboardActivityItem[] = [];

    if (costSummary && !hasData) {
      items.push({
        id: 'no-usage',
        kind: 'empty',
        title: 'No usage data yet',
        description: 'Provider usage has not been recorded for this workspace.',
        timestampLabel: 'Now',
        period: '7d',
        tone: 'muted',
      });
    }

    if (costSummary) {
      items.push({
        id: 'cost-summary-loaded',
        kind: 'cost',
        title: 'Cost summary refreshed',
        description: hasData
          ? `Loaded ${activeProviders} provider${activeProviders === 1 ? '' : 's'} with usage data.`
          : 'Dashboard cost summary loaded successfully.',
        timestampLabel: 'Now',
        period: '7d',
        tone: hasData ? 'success' : 'muted',
      });
    }

    costData.forEach((provider, index) => {
      items.push({
        id: `cost-${provider.name}`,
        kind: 'cost',
        title: `${formatProviderName(provider.name)} cost tracked`,
        description: `$${provider.value.toFixed(4)} recorded for this provider.`,
        timestampLabel: index < 2 ? 'This week' : 'Last 30 days',
        period: index < 2 ? '7d' : '30d',
        tone: 'success',
      });
    });

    usageData.forEach((provider, index) => {
      items.push({
        id: `requests-${provider.name}`,
        kind: 'request',
        title: `${formatProviderName(provider.name)} requests updated`,
        description: `${Number(provider.value).toLocaleString()} request${provider.value === 1 ? '' : 's'} counted.`,
        timestampLabel: index < 2 ? 'This week' : 'Last 30 days',
        period: index < 2 ? '7d' : '30d',
        tone: 'success',
      });
    });

    (
      [
        ['models', systemStatus.models],
        ['routing', systemStatus.routing],
        ['sandbox', systemStatus.sandbox],
      ] as const
    ).forEach(([service, state]) => {
      items.push({
        id: `status-${service}`,
        kind: 'status',
        title: `${formatProviderName(service)} status: ${state}`,
        description: `System status signal for ${service} is currently ${state}.`,
        timestampLabel: 'Live',
        period: 'all',
        tone: statusTone(state),
      });
    });

    return items;
  }, [activeProviders, costData, costSummary, hasData, systemStatus, usageData]);

  const visibleActivityItems = React.useMemo(() => {
    if (period === 'all') return activityItems;
    if (period === '30d') return activityItems.filter((item) => item.period !== 'all');
    return activityItems.filter((item) => item.period === '7d');
  }, [activityItems, period]);

  return (
    <div className="min-h-[400px] p-8 text-text">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div
          className="inline-flex rounded-lg border border-border bg-surface p-1"
          aria-label="Dashboard period"
        >
          {DASHBOARD_PERIODS.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => setPeriod(item.value)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                period === item.value
                  ? 'bg-primary text-text-inverse'
                  : 'text-muted hover:bg-surface-hover hover:text-text'
              }`}
              aria-pressed={period === item.value}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      {showOnboardingPrompt && (
        <Card variant="default" padding="md" className="mb-6 border-primary/40 bg-primary/10">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <Rocket className="mt-0.5 h-5 w-5 text-primary" aria-hidden="true" />
              <div>
                <h2 className="text-sm font-semibold text-text">Finish first-run setup</h2>
                <p className="text-sm text-muted">
                  Walk through provider setup, a first chat, and a search demo.
                </p>
              </div>
            </div>
            <Link
              href="/onboarding"
              className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold text-text-inverse"
            >
              Open onboarding
            </Link>
          </div>
        </Card>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Cost" value={`$${totalCost.toFixed(4)}`} hint="All providers" />
        <StatCard
          label="Total Requests"
          value={totalRequests.toLocaleString()}
          hint="Across all providers"
        />
        <StatCard label="Active Providers" value={activeProviders} hint="With cost data" />
        <Card
          role="group"
          aria-label="System status"
          className="min-h-[64px]"
          variant="default"
          padding="md"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted">System Status</span>
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${statusDot(systemStatus.models)}`} />
              <span className={`w-2 h-2 rounded-full ${statusDot(systemStatus.routing)}`} />
              <span className={`w-2 h-2 rounded-full ${statusDot(systemStatus.sandbox)}`} />
            </div>
          </div>
          <div className="mt-1 flex gap-2 text-[11px] text-muted">
            <span>Models</span>
            <span>Routing</span>
            <span>Sandbox</span>
          </div>
        </Card>
      </div>

      <TristateWrapper
        loading={costLoading}
        error={costError}
        plain
        loadingTitle="Loading dashboard"
        loadingDescription="Fetching cost and usage data."
        errorTitle="Failed to load data"
        onRetry={() => undefined}
      >
        {!hasData ? (
          <EmptyState
            icon={<BarChart3 className="w-8 h-8" />}
            title="No usage data yet"
            description="Start using AI providers to see cost and usage breakdown here."
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card variant="default" padding="md" className="shadow-card">
              <CostBreakdownChart data={costData} />
            </Card>
            <Card variant="default" padding="md" className="shadow-card">
              <ProviderUsageChart data={usageFallbackData} metric={usageMetric} />
            </Card>
          </div>
        )}
      </TristateWrapper>

      <Card variant="default" padding="md" className="mt-8 shadow-card">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" aria-hidden="true" />
              <h2 className="text-lg font-semibold text-text">Recent Activity</h2>
            </div>
            <p className="mt-1 text-sm text-muted">
              Derived from current cost, request, and status signals.
            </p>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full border border-border px-2.5 py-1 text-xs text-muted">
            <Clock className="h-3.5 w-3.5" aria-hidden="true" />
            {DASHBOARD_PERIODS.find((item) => item.value === period)?.label}
          </span>
        </div>
        <ol className="space-y-3">
          {visibleActivityItems.map((item) => (
            <li key={item.id} className="flex gap-3 rounded-md border border-border bg-bg p-3">
              <span
                className={`mt-1 h-2.5 w-2.5 flex-none rounded-full ${activityDotClass(item.tone)}`}
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                  <h3 className="text-sm font-semibold text-text">{item.title}</h3>
                  <span className="text-xs text-muted">{item.timestampLabel}</span>
                </div>
                <p className="mt-1 text-sm text-muted">{item.description}</p>
              </div>
            </li>
          ))}
        </ol>
      </Card>
    </div>
  );
};

export default DashboardContent;

// Prevent static generation - this page uses react-query
export const getServerSideProps = async () => {
  return { props: {} };
};
