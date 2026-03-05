import { useState } from 'react';
import type { ProviderConfig } from '../../../hooks/api/useSettings';
import { useProviderSettings } from '../../../hooks/api/useSettings';
import { useRoutingHealth } from '../../../hooks/api/useHealth';
import TwoColumnLayout from '../../../components/TwoColumnLayout';
import { Button, Alert } from '../../../components/ui';
import ProviderSidebar from './components/ProviderSidebar';
import ProviderDetails from './components/ProviderDetails';
import ProviderPromptTest from './components/ProviderPromptTest';
import ProviderTestResultBanner from './components/ProviderTestResultBanner';
import { useProviderMutations } from './hooks/useProviderMutations';
import { useProviderReorder } from './hooks/useProviderReorder';

export default function ProvidersManagerScreen() {
  const { data: providers, isLoading, error, refetch } = useProviderSettings();
  const { data: routingHealth } = useRoutingHealth();

  const providerList = (providers as ProviderConfig[] | undefined) || [];
  const routingStatus: string = (routingHealth as any)?.status || 'Healthy';

  const [selectedProvider, setSelectedProvider] = useState<ProviderConfig | null>(null);
  const [testPrompt, setTestPrompt] = useState('Write a hello world in Python');

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

      {selectedProvider ? (
        <div className="space-y-6">
          {testResult && (
            <ProviderTestResultBanner
              result={testResult}
              onDismiss={() => setTestResult(null)}
            />
          )}

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
                {selectedProvider.models.map(model => (
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

