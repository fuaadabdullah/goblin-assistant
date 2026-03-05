"use client";

import { useState, ReactNode } from 'react';
import { useProviderSettings, ProviderConfig } from '@/hooks/api/useSettings';
import { useRoutingHealth } from '@/hooks/api/useHealth';
import { chatAPI } from '@/api/client-axios';
import TwoColumnLayout from '@/components/TwoColumnLayout';

/**
 * Provider Manager: Select, test, and prioritize AI providers
 * Migrated from src/pages/ProvidersPage.tsx
 */
export default function ProvidersPage() {
  const { settings: providers, isLoading, error, refetch } = useProviderSettings();
  const { settings: routingHealth } = useRoutingHealth();
  // Cast query data (React Query defaults unknown without generics)
  const providerList = providers as ProviderConfig[] | undefined;
  const routingStatus: string = (routingHealth as any)?.status || 'Healthy';
  const [selectedProvider, setSelectedProvider] = useState<ProviderConfig | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
    latency?: number;
  } | null>(null);

  const handleTestConnection = async (provider: ProviderConfig) => {
    setTesting(provider.name);
    setTestResult(null);

    try {
      // Use real backend endpoint when providerId is available
      if (provider.id) {
        const result = await chatAPI.testProviderConnection(provider.name);
        setTestResult(result);
      } else {
        // Fallback for providers without IDs (shouldn't happen in production)
        setTestResult({
          success: false,
          message: 'Provider ID not available. Cannot test connection.',
        });
      }
    } catch (error) {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Connection test failed',
      });
    } finally {
      setTesting(null);
    }
  };

  const sidebar: ReactNode = (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-text mb-3">Providers</h2>
        <p className="text-xs text-muted mb-4">
          Manage AI provider connections, priorities, and health
        </p>
      </div>

      {/* Quick Actions */}
      <div className="space-y-2">
        <button
          onClick={() => refetch()}
          className="w-full px-3 py-2 text-sm font-medium text-primary bg-primary/20 rounded-lg hover:bg-primary/30 transition-colors"
        >
          🔄 Refresh Status
        </button>
        <button className="w-full px-3 py-2 text-sm font-medium text-text bg-surface-hover rounded-lg hover:bg-surface-active transition-colors">
          ➕ Add Provider
        </button>
      </div>

      {/* Routing Health */}
      {routingHealth ? (
        <div className="bg-surface rounded-lg p-3 border border-border">
          <h3 className="text-sm font-medium text-text mb-2">Routing Engine</h3>
          <div className="text-xs text-muted">
            <div className="flex justify-between">
              <span>Status:</span>
              <span className="font-medium text-success">{routingStatus}</span>
            </div>
          </div>
        </div>
      ) : null}

      {/* Provider List */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-text uppercase tracking-wide">
          Active Providers
        </h3>
        {isLoading ? (
          <div className="text-xs text-muted">Loading...</div>
        ) : providerList && providerList.length > 0 ? (
          providerList.map((provider: ProviderConfig) => (
            <button
              key={provider.id || provider.name}
              onClick={() => setSelectedProvider(provider)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                selectedProvider?.name === provider.name
                  ? 'bg-primary/20 text-primary border border-primary'
                  : 'bg-surface border border-border text-text hover:bg-surface-hover'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{provider.name}</span>
                <span className={`text-xs ${provider.enabled ? 'text-success' : 'text-muted'}`}>
                  {provider.enabled ? '✓' : '○'}
                </span>
              </div>
            </button>
          ))
        ) : (
          <div className="text-xs text-muted">No providers configured</div>
        )}
      </div>
    </div>
  );

  const mainContent = (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text mb-2">Provider Manager</h1>
        <p className="text-muted">
          Configure, test, and prioritize AI providers for intelligent routing
        </p>
      </div>

      {error && (
        <div className="bg-surface border border-danger rounded-lg p-4">
          <p className="text-danger">Failed to load providers: {(error as Error).message}</p>
        </div>
      )}

      {selectedProvider ? (
        <div className="bg-surface rounded-xl shadow-sm border border-border p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-semibold text-text">{selectedProvider.name}</h2>
              <p className="text-sm text-muted">Provider Configuration</p>
            </div>
            <button
              onClick={() => handleTestConnection(selectedProvider)}
              disabled={testing === selectedProvider.name}
              className="px-4 py-2 bg-success text-text-inverse rounded-lg hover:bg-success/90 disabled:bg-surface-hover disabled:cursor-not-allowed transition-colors text-sm font-medium flex items-center gap-2 shadow-glow-primary"
            >
              {testing === selectedProvider.name ? (
                <>
                  <span className="animate-spin">🔄</span>
                  Testing...
                </>
              ) : (
                <>
                  <span>🧪</span>
                  Test Connection
                </>
              )}
            </button>
          </div>

          {/* Test Result Banner */}
          {testResult && (
            <div
              className={`mb-6 p-4 rounded-lg border ${
                testResult.success ? 'bg-success/20 border-success' : 'bg-danger/20 border-danger'
              }`}
            >
              <div className="flex items-start gap-3">
                <span className="text-xl">{testResult.success ? '✓' : '✗'}</span>
                <div className="flex-1">
                  <h3
                    className={`text-sm font-semibold mb-1 ${
                      testResult.success ? 'text-success' : 'text-danger'
                    }`}
                  >
                    {testResult.success ? 'Connection Successful' : 'Connection Failed'}
                  </h3>
                  <p className={`text-sm ${testResult.success ? 'text-success' : 'text-danger'}`}>
                    {testResult.message}
                  </p>
                  {testResult.latency && (
                    <p className="text-xs text-muted mt-1">Latency: {testResult.latency}ms</p>
                  )}
                </div>
                <button
                  onClick={() => setTestResult(null)}
                  className={
                    testResult.success
                      ? 'text-success hover:text-success/80'
                      : 'text-danger hover:text-danger/80'
                  }
                  aria-label="Dismiss"
                >
                  ✕
                </button>
              </div>
            </div>
          )}

          <div className="space-y-6">
            {/* Status */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-bg rounded-lg p-4">
                <div className="text-xs text-muted mb-1">Status</div>
                <div
                  className={`text-lg font-semibold ${selectedProvider.enabled ? 'text-success' : 'text-muted'}`}
                >
                  {selectedProvider.enabled ? 'Enabled' : 'Disabled'}
                </div>
              </div>
              <div className="bg-bg rounded-lg p-4">
                <div className="text-xs text-muted mb-1">Priority</div>
                <div className="text-lg font-semibold text-text">
                  {selectedProvider.priority || 'N/A'}
                </div>
              </div>
              <div className="bg-bg rounded-lg p-4">
                <div className="text-xs text-muted mb-1">Models</div>
                <div className="text-lg font-semibold text-text">
                  {selectedProvider.models?.length || 0}
                </div>
              </div>
            </div>

            {/* Configuration */}
            <div>
              <h3 className="text-sm font-semibold text-text mb-3">Configuration</h3>
              <div className="space-y-3">
                <div>
                  <label
                    htmlFor="provider-base-url"
                    className="block text-xs font-medium text-text mb-1"
                  >
                    Base URL
                  </label>
                  <input
                    id="provider-base-url"
                    type="text"
                    value={selectedProvider.base_url || 'Not configured'}
                    readOnly
                    aria-readonly="true"
                    className="w-full px-3 py-2 border border-border rounded-lg bg-surface-hover text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-text mb-1">API Key Status</label>
                  <div
                    className={`px-3 py-2 border rounded-lg text-sm ${
                      selectedProvider.api_key
                        ? 'border-success bg-success/20 text-success'
                        : 'border-danger bg-danger/20 text-danger'
                    }`}
                  >
                    {selectedProvider.api_key ? '✓ Configured' : '✗ Not configured'}
                  </div>
                </div>
              </div>
            </div>

            {/* Available Models */}
            {selectedProvider.models && selectedProvider.models.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-text mb-3">Available Models</h3>
                <div className="flex flex-wrap gap-2">
                  {selectedProvider.models.map((model) => (
                    <span
                      key={model}
                      className="px-3 py-1 bg-primary/20 text-primary rounded-full text-xs font-medium"
                    >
                      {model}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-surface rounded-xl shadow-sm border border-border p-12 text-center">
          <div className="text-6xl mb-4">🔌</div>
          <h3 className="text-lg font-medium text-text mb-2">Select a Provider</h3>
          <p className="text-muted">Choose a provider from the sidebar to test and configure</p>
        </div>
      )}
    </div>
  );

  return <TwoColumnLayout sidebar={sidebar}>{mainContent}</TwoColumnLayout>;
}