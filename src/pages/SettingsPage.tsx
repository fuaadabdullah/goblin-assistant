import React, { useState, useEffect } from 'react';
import { Settings, Globe, CheckCircle, XCircle, RefreshCw, Loader2, Shield, AlertTriangle } from 'lucide-react';
import { useToast } from '../contexts/ToastContext';
import { api } from '../api/http-client';

interface ProviderSettings {
  name: string;
  api_key?: string;
  base_url?: string;
  models: string[];
  enabled: boolean;
}

interface ModelSettings {
  name: string;
  provider: string;
  model_id: string;
  temperature?: number;
  max_tokens?: number;
  enabled: boolean;
}

interface ApiKeyStatus {
  [providerName: string]: {
    configured: boolean;
    enabled: boolean;
    models: string[];
  };
}

interface SettingsResponse {
  providers: ProviderSettings[];
  models: ModelSettings[];
  default_provider?: string;
  default_model?: string;
}

const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [apiKeyStatus, setApiKeyStatus] = useState<ApiKeyStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testingConnection, setTestingConnection] = useState<string | null>(null);

  const { showError, showSuccess } = useToast();

  useEffect(() => {
    fetchSettings();
    fetchApiKeyStatus();
  }, []);

  const fetchSettings = async () => {
    const baseUrl = import.meta.env.VITE_FASTAPI_URL || import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
    console.debug('SettingsPage: using baseUrl', baseUrl);
    try {
      const response = await fetch(`${baseUrl}/settings`);
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
        setLoading(false);
      } else {
        throw new Error('Failed to fetch settings');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load settings';
      setError(errorMessage);
      showError('Failed to Load Settings', errorMessage);
      setLoading(false);
    }
  };

  const fetchApiKeyStatus = async () => {
    const baseUrl = import.meta.env.VITE_FASTAPI_URL || import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
    try {
      const response = await fetch(`${baseUrl}/settings/api-keys/status`);
      if (response.ok) {
        const data = await response.json();
        setApiKeyStatus(data);
      } else {
        throw new Error('Failed to fetch API key status');
      }
    } catch (err) {
      console.error('Failed to fetch API key status:', err);
      // Don't show error for API key status, it's not critical
    }
  };

  const updateProviderSettings = async (
    providerName: string,
    updates: Partial<ProviderSettings>
  ) => {
    if (!settings) return;

    try {
      setSaving(true);
  const baseUrl = import.meta.env.VITE_FASTAPI_URL || import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
  const response = await fetch(`${baseUrl}/settings/providers/${providerName}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (response.ok) {
        // Update local state to reflect the changes
        setSettings({
          ...settings,
          providers: settings.providers.map(p => (p.name === providerName ? { ...p, ...updates } : p)),
        });
        showSuccess('Settings Updated', `Settings updated successfully for ${providerName}`);
        // Refresh API key status after update
        fetchApiKeyStatus();
      } else {
        throw new Error('Failed to update provider settings');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update settings';
      setError(errorMessage);
      showError('Update Failed', errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const updateModelSettings = async (modelName: string, updates: Partial<ModelSettings>) => {
    if (!settings) return;

    try {
      setSaving(true);
  const baseUrl = import.meta.env.VITE_FASTAPI_URL || import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
  const response = await fetch(`${baseUrl}/settings/models/${modelName}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (response.ok) {
        // Update local state to reflect the changes
        setSettings({
          ...settings,
          models: settings.models.map(m => (m.name === modelName ? { ...m, ...updates } : m)),
        });
        showSuccess('Settings Updated', `Settings updated successfully for ${modelName}`);
      } else {
        throw new Error('Failed to update model settings');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update settings';
      setError(errorMessage);
      showError('Update Failed', errorMessage);
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async (providerName: string) => {
    try {
      setTestingConnection(providerName);
  const baseUrl = import.meta.env.VITE_FASTAPI_URL || import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001';
  const response = await fetch(`${baseUrl}/settings/test-connection`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ provider_name: providerName }),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.connected) {
          showSuccess('Connection Test Successful', result.message || `Successfully connected to ${providerName}`);
        } else {
          throw new Error(result.message || 'Connection test failed');
        }
      } else {
        throw new Error('Failed to test connection');
      }
    } catch (err) {
      const errorMessage = `Connection test failed: ${err instanceof Error ? err.message : 'Unknown error'}`;
      setError(errorMessage);
      showError('Connection Test Failed', errorMessage);
    } finally {
      setTestingConnection(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-blue-600" />
          <p className="mt-2 text-gray-600">Loading settings...</p>
        </div>
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <XCircle className="mx-auto h-12 w-12 text-red-500" />
          <p className="mt-2 text-gray-900">Failed to load settings</p>
          <button
            onClick={fetchSettings}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Provider & Model Settings</h1>
          <p className="text-gray-600">
            Configure API keys, models, and connection settings for your AI providers
          </p>
        </div>

        {/* Error Messages */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-center">
              <XCircle className="h-5 w-5 text-red-400 mr-2" />
              <p className="text-red-800">{error}</p>
            </div>
          </div>
        )}

        {/* API Key Status */}
        <div className="mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">API Key Configuration</h2>
          <div className="bg-white rounded-lg shadow-sm border p-6">
            <div className="flex items-center mb-4">
              <Shield className="h-6 w-6 text-blue-600 mr-2" />
              <h3 className="text-lg font-medium text-gray-900">Environment Variables</h3>
            </div>
            <p className="text-gray-600 mb-4">
              API keys are configured via environment variables for security. Update your <code className="bg-gray-100 px-2 py-1 rounded">.env</code> file with your API keys.
            </p>

            {apiKeyStatus && (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {Object.entries(apiKeyStatus).map(([provider, status]) => (
                  <div key={provider} className="border rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-medium text-gray-900 capitalize">{provider}</h4>
                      <div className="flex items-center gap-2">
                        {status.configured ? (
                          <CheckCircle className="h-5 w-5 text-green-500" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-500" />
                        )}
                        <span className={`text-sm ${status.configured ? 'text-green-600' : 'text-red-600'}`}>
                          {status.configured ? 'Configured' : 'Missing'}
                        </span>
                      </div>
                    </div>

                    {!status.configured && (
                      <div className="flex items-center text-amber-600 text-sm mb-2">
                        <AlertTriangle className="h-4 w-4 mr-1" />
                        API key not found in environment
                      </div>
                    )}

                    <div className="text-sm text-gray-600">
                      <div>Status: {status.enabled ? 'Enabled' : 'Disabled'}</div>
                      <div>Models: {status.models.length}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <h4 className="font-medium text-blue-900 mb-2">Environment Variables Required:</h4>
              <div className="text-sm text-blue-800 font-mono">
                OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY,<br />
                GROQ_API_KEY, DEEPSEEK_API_KEY, SILICONFLOW_API_KEY,<br />
                MOONSHOT_API_KEY, FIREWORKS_API_KEY, ELEVENLABS_API_KEY,<br />
                DATADOG_API_KEY, NETLIFY_API_KEY
              </div>
            </div>
          </div>
        </div>

        {/* Provider Settings */}
        <div className="mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">AI Providers</h2>
          <div className="grid gap-6 md:grid-cols-2">
            {settings.providers.map(provider => (
              <div key={provider.name} className="bg-white rounded-lg shadow-sm border p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900">{provider.name}</h3>
                  <div className="flex items-center gap-2">
                    {provider.enabled ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <span
                      className={`text-sm ${provider.enabled ? 'text-green-600' : 'text-red-600'}`}
                    >
                      {provider.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                </div>

                <div className="space-y-4">
                  {/* Base URL */}
                  <div>
                    <label
                      htmlFor={`base-url-${provider.name}`}
                      className="block text-sm font-medium text-gray-700 mb-2"
                    >
                      Base URL
                    </label>
                    <div className="relative">
                      <Globe className="absolute left-3 top-3 h-5 w-5 text-gray-400" />
                      <input
                        id={`base-url-${provider.name}`}
                        type="url"
                        value={provider.base_url || ''}
                        onChange={e =>
                          updateProviderSettings(provider.name, { base_url: e.target.value })
                        }
                        placeholder="https://api.example.com/v1"
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        disabled={saving}
                      />
                    </div>
                  </div>

                  {/* Models */}
                  <div>
                    <div className="block text-sm font-medium text-gray-700 mb-2">
                      Available Models
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {provider.models.map(model => (
                        <span
                          key={model}
                          className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800"
                        >
                          {model}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2 pt-4">
                    <button
                      onClick={() => testConnection(provider.name)}
                      disabled={testingConnection === provider.name || saving}
                      className="flex-1 bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {testingConnection === provider.name ? (
                        <>
                          <RefreshCw className="h-4 w-4 animate-spin" />
                          Testing...
                        </>
                      ) : (
                        <>
                          <RefreshCw className="h-4 w-4" />
                          Test Connection
                        </>
                      )}
                    </button>
                    <button
                      onClick={() =>
                        updateProviderSettings(provider.name, { enabled: !provider.enabled })
                      }
                      disabled={saving}
                      className={`flex-1 py-2 px-4 rounded-lg focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${
                        provider.enabled
                          ? 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
                          : 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500'
                      }`}
                    >
                      <Settings className="h-4 w-4" />
                      {provider.enabled ? 'Disable' : 'Enable'}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Model Settings */}
        <div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Model Configuration</h2>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {settings.models.map(model => (
              <div key={model.name} className="bg-white rounded-lg shadow-sm border p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900">{model.name}</h3>
                  <div className="flex items-center gap-2">
                    {model.enabled ? (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <span
                      className={`text-sm ${model.enabled ? 'text-green-600' : 'text-red-600'}`}
                    >
                      {model.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <span className="text-sm text-gray-600">Provider: </span>
                    <span className="text-sm font-medium text-gray-900">{model.provider}</span>
                  </div>

                  <div>
                    <span className="text-sm text-gray-600">Model ID: </span>
                    <span className="text-sm font-medium text-gray-900">{model.model_id}</span>
                  </div>

                  {/* Temperature */}
                  <div>
                    <label
                      htmlFor={`temperature-${model.name}`}
                      className="block text-sm font-medium text-gray-700 mb-2"
                    >
                      Temperature: {model.temperature || 0.7}
                    </label>
                    <input
                      id={`temperature-${model.name}`}
                      type="range"
                      min="0"
                      max="2"
                      step="0.1"
                      value={model.temperature || 0.7}
                      onChange={e =>
                        updateModelSettings(model.name, { temperature: parseFloat(e.target.value) })
                      }
                      className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                      disabled={saving}
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>0 (Deterministic)</span>
                      <span>2 (Creative)</span>
                    </div>
                  </div>

                  {/* Max Tokens */}
                  <div>
                    <label
                      htmlFor={`max-tokens-${model.name}`}
                      className="block text-sm font-medium text-gray-700 mb-2"
                    >
                      Max Tokens
                    </label>
                    <input
                      id={`max-tokens-${model.name}`}
                      type="number"
                      value={model.max_tokens || ''}
                      onChange={e =>
                        updateModelSettings(model.name, {
                          max_tokens: parseInt(e.target.value) || undefined,
                        })
                      }
                      placeholder="4096"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      disabled={saving}
                    />
                  </div>

                  {/* Enable/Disable */}
                  <button
                    onClick={() => updateModelSettings(model.name, { enabled: !model.enabled })}
                    disabled={saving}
                    className={`w-full py-2 px-4 rounded-lg focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${
                      model.enabled
                        ? 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
                        : 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500'
                    }`}
                  >
                    <Settings className="h-4 w-4" />
                    {model.enabled ? 'Disable Model' : 'Enable Model'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
