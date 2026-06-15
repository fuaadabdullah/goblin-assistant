import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { ProviderConfig } from '../../../hooks/api/useSettings';
import type { RoutingHealthStatus } from '../../../types/api';
import { useProviderSettings } from '../../../hooks/api/useSettings';
import { useRoutingHealth } from '../../../hooks/api/useHealth';
import { useProviderStatus } from '../../../hooks/useProviderStatus';
import { useSupabaseRealtime } from '../../../hooks/useSupabaseRealtime';
import { queryKeys } from '../../../lib/query-keys';
import TwoColumnLayout from '../../../components/TwoColumnLayout';
import { Button, Alert } from '../../../components/ui';
import ProviderSidebar from './components/ProviderSidebar';
import ProviderDetails from './components/ProviderDetails';
import ProviderPromptTest from './components/ProviderPromptTest';
import ProviderTestResultBanner from './components/ProviderTestResultBanner';
import RoutingAuditTab from './components/RoutingAuditTab';
import { useProviderMutations } from './hooks/useProviderMutations';
import { useProviderReorder } from './hooks/useProviderReorder';
import { getProviderRouterConfigError } from '../../../services/provider-router';

export default function ProvidersManagerScreen() {
  const queryClient = useQueryClient();
  const { data: providers, isLoading, error, refetch } = useProviderSettings();
  const { data: routingHealth } = useRoutingHealth();
  const { statuses: providerStatuses, connected: realtimeConnected } = useProviderStatus();

  const providerList = (providers as ProviderConfig[] | undefined) || [];
  const routingStatus: string =
    (routingHealth as RoutingHealthStatus | undefined)?.status || 'Healthy';
  const providerConfigError = getProviderRouterConfigError();

  const [selectedProvider, setSelectedProvider] = useState<ProviderConfig | null>(null);
  const [testPrompt, setTestPrompt] = useState('Write a hello world in Python');
  const [activeTab, setActiveTab] = useState<'details' | 'audit'>('details');

  useSupabaseRealtime('provider_status', (payload) => {
    if (payload.eventType === 'INSERT' || payload.eventType === 'UPDATE') {
      queryClient.invalidateQueries({ queryKey: queryKeys.routingAnalytics });
    }
  });

  const {
    testing,
    testResult,
    setTestResult,
    quickTest,
    promptTest,
    setPriority,
    reorderProviders,
    isReordering,
  } = useProviderMutations();

  const { draggedProvider, handleDragStart, handleDragOver, handleDrop } = useProviderReorder({
    providers: providerList,
    onReorder: reorderProviders,
  });

  const sidebar = (
    <ProviderSidebar
      providers={providerList}
      isLoading={isLoading}
      selectedProvider={selectedProvider}
      onSelectProvider={setSelectedProvider}
      onRefresh={() => refetch()}
      routingStatus={routingStatus}
      showRoutingHealth={Boolean(routingHealth)}
      testingProviderName={testing}
      onQuickTest={quickTest}
      draggedProvider={draggedProvider}
      isReordering={isReordering}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      providerStatuses={providerStatuses}
      realtimeConnected={realtimeConnected}
    />
  );

  const mainContent = (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text mb-2">Provider Manager & Tester</h1>
        <p className="text-muted">
          Configure, test with prompts, and set priorities for intelligent routing
        </p>
      </div>

      {/* Live region for provider updates */}
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {!isLoading &&
          providerList.length > 0 &&
          `Providers loaded. ${providerList.length} provider${
            providerList.length !== 1 ? 's' : ''
          } available`}
        {testResult && `Test ${testResult.success ? 'passed' : 'failed'}. ${testResult.message}`}
      </div>

      {error && (
        <Alert
          variant="danger"
          title="Failed to Load Providers"
          message={
            <>
              <p className="mb-3">{(error as Error).message}</p>
              <Button
                variant="danger"
                size="sm"
                icon="🔄"
                onClick={() => refetch()}
                aria-label="Retry loading providers"
              >
                Retry
              </Button>
            </>
          }
          dismissible
        />
      )}

      {providerConfigError && (
        <Alert
          variant="danger"
          title="Provider routing config is incompatible"
          message={
            <>
              <p className="mb-2">{providerConfigError.message}</p>
              <p className="text-sm text-muted">
                Regenerate <code>config/providers.json</code> from
                <code>config/providers.toml</code> and refresh the page.
              </p>
            </>
          }
          dismissible={false}
        />
      )}

      {selectedProvider ? (
        <div className="space-y-6">
          {testResult && (
            <ProviderTestResultBanner result={testResult} onDismiss={() => setTestResult(null)} />
          )}

          {/* Tabs */}
          <div className="flex gap-2 border-b border-border">
            <button
              type="button"
              onClick={() => setActiveTab('details')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'details'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted hover:text-text'
              }`}
            >
              Provider Details
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('audit')}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'audit'
                  ? 'border-primary text-primary'
                  : 'border-transparent text-muted hover:text-text'
              }`}
            >
              Routing Audit
            </button>
          </div>

          {/* Details Tab */}
          {activeTab === 'details' && (
            <div className="space-y-6">
              <ProviderDetails provider={selectedProvider} onSetPriority={setPriority} />

              <ProviderPromptTest
                prompt={testPrompt}
                onPromptChange={setTestPrompt}
                onTest={() => {
                  if (!selectedProvider) return;
                  promptTest(selectedProvider, testPrompt);
                }}
                isTesting={testing === selectedProvider.name}
                disabled={testing === selectedProvider.name}
              />

              {selectedProvider.models && selectedProvider.models.length > 0 && (
                <div className="bg-surface rounded-xl shadow-sm border border-border p-6">
                  <h3 className="text-lg font-semibold text-text mb-4">
                    Available Models ({selectedProvider.models.length})
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedProvider.models.map((model) => (
                      <span
                        key={model}
                        className="px-3 py-1.5 bg-primary/20 text-primary rounded-full text-sm font-medium"
                      >
                        {model}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Audit Trail Tab */}
          {activeTab === 'audit' && <RoutingAuditTab providerId={selectedProvider.name} />}
        </div>
      ) : (
        <div className="bg-surface rounded-xl shadow-sm border border-border p-12 text-center">
          <div className="text-6xl mb-4" aria-hidden="true">
            🔌
          </div>
          <h3 className="text-lg font-medium text-text mb-2">Select a Provider</h3>
          <p className="text-muted">Choose a provider from the sidebar to test and configure</p>
        </div>
      )}
    </div>
  );

  return <TwoColumnLayout sidebar={sidebar}>{mainContent}</TwoColumnLayout>;
}
