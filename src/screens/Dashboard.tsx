import React from 'react';
import { useQuery } from '@tanstack/react-query';
import CostBreakdownChart from '@/components/cost/CostBreakdownChart';
import ProviderUsageChart from '@/components/cost/ProviderUsageChart';
import { getChartPaletteColor } from '@/components/cost/chartPalette';
import { runtimeClient } from '@/api';

const DashboardContent: React.FC = () => {
  const {
    data: costSummary,
    isLoading: costLoading,
    error: costError,
  } = useQuery({
    queryKey: ['costSummary'],
    queryFn: () => runtimeClient.getCostSummary(),
  });

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
  const usageFallbackData = usageMetric === 'requests'
    ? usageData
    : costData.map(({ name, value }) => ({ name, value }));

  return (
    <div className="min-h-[400px] p-8 text-text">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
      </div>

      {costLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="h-72 animate-pulse rounded-lg border border-border bg-surface-hover" />
          <div className="h-72 animate-pulse rounded-lg border border-border bg-surface-hover" />
        </div>
      ) : costError ? (
        <div className="rounded-md border border-danger/40 bg-danger/10 p-4 text-danger">
          Error loading data: {(costError as Error)?.message || String(costError)}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-lg border border-border bg-surface p-4 shadow-card">
            <CostBreakdownChart data={costData} />
          </div>
          <div className="rounded-lg border border-border bg-surface p-4 shadow-card">
            <ProviderUsageChart data={usageFallbackData} metric={usageMetric} />
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardContent;

// Prevent static generation - this page uses react-query
export const getServerSideProps = async () => {
  return { props: {} };
};
