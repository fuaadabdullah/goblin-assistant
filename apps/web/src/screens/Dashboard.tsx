import React from 'react';
import { useQuery } from '@tanstack/react-query';
import CostBreakdownChart from '@/components/cost/CostBreakdownChart';
import ProviderUsageChart from '@/components/cost/ProviderUsageChart';
import { getChartPaletteColor } from '@/components/cost/chartPalette';
import { runtimeClient } from '@/api';
import { TristateWrapper, Card } from '@/components/ui';

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
  const usageFallbackData =
    usageMetric === 'requests' ? usageData : costData.map(({ name, value }) => ({ name, value }));

  return (
    <div className="min-h-[400px] p-8 text-text">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card variant="default" padding="md" className="shadow-card">
            <CostBreakdownChart data={costData} />
          </Card>
          <Card variant="default" padding="md" className="shadow-card">
            <ProviderUsageChart data={usageFallbackData} metric={usageMetric} />
          </Card>
        </div>
      </TristateWrapper>
    </div>
  );
};

export default DashboardContent;

// Prevent static generation - this page uses react-query
export const getServerSideProps = async () => {
  return { props: {} };
};
