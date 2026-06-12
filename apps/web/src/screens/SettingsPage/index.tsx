import React from 'react';
import { Loader2 } from 'lucide-react';
import { useProviderSettings } from '../../hooks/api/useSettings';
import ThemePreview from '../../components/ThemePreview';
import KeyboardShortcutsHelp from '../../components/KeyboardShortcutsHelp';
import ContrastModeToggle from '../../components/ContrastModeToggle';
import Seo from '../../components/Seo';
import { useProvider } from '../../contexts/ProviderContext';
import { useToast } from '../../hooks/useToast';
import { apiClient } from '@/lib/api';
import { Card, InlineErrorState, PageState } from '../../components/ui';
import { ProviderStatusSection } from './ProviderStatusSection';
import { ModelPreferencesSection } from './ModelPreferencesSection';
import type { ProviderSource, ProviderDisplay, ProviderGroup, ProviderGroupId } from './types';
import { DEFAULT_OPEN_PROVIDER_GROUPS } from './constants';
import {
  normalizeProviderName,
  providerMatchesSearch,
  isLocalProvider,
  isCloudProvider,
} from './providerUtils';

const SettingsPageContent: React.FC = () => {
  const {
    data: providerData,
    isLoading: providersLoading,
    error: providersError,
    refetch,
  } = useProviderSettings();
  const providerCtx = useProvider();
  const { showSuccess, showError } = useToast();
  const [isSaving, setIsSaving] = React.useState(false);
  const [providerSearch, setProviderSearch] = React.useState('');
  const [openProviderGroups, setOpenProviderGroups] = React.useState<ProviderGroupId[]>(
    DEFAULT_OPEN_PROVIDER_GROUPS
  );
  const [expandedProviderKey, setExpandedProviderKey] = React.useState<string | null>(null);

  const providerRows: ProviderSource[] = React.useMemo(() => {
    if (Array.isArray(providerData)) return providerData as ProviderSource[];

    if (providerData && typeof providerData === 'object') {
      const maybeProviders = (providerData as { providers?: unknown }).providers;
      if (Array.isArray(maybeProviders)) return maybeProviders as ProviderSource[];

      return Object.entries(providerData as Record<string, unknown>).map(([name, raw]) => {
        if (raw && typeof raw === 'object') return { name, ...(raw as ProviderSource) };
        return { name };
      });
    }

    return [];
  }, [providerData]);

  const providers: ProviderDisplay[] = providerRows.map((p: ProviderSource) => {
    const name = typeof p.name === 'string' ? p.name : 'Unknown';
    const models = Array.isArray(p.models)
      ? p.models.filter((model): model is string => typeof model === 'string')
      : [];
    return {
      name,
      normalizedName: normalizeProviderName(name),
      configured: Boolean(p.enabled ?? p.configured ?? false),
      env_var: p.env_var || p.api_key ? `${name.toUpperCase()}_API_KEY` : undefined,
      base_url: p.base_url,
      models,
    };
  });

  const filteredProviders = React.useMemo(
    () => providers.filter((provider) => providerMatchesSearch(provider, providerSearch)),
    [providerSearch, providers]
  );

  const providerGroups = React.useMemo<ProviderGroup[]>(
    () => [
      {
        id: 'configured',
        title: 'Configured',
        description: 'Ready for routing and model selection.',
        providers: filteredProviders.filter((p) => p.configured),
      },
      {
        id: 'needs-setup',
        title: 'Needs setup',
        description: 'Missing credentials or disabled in the provider registry.',
        providers: filteredProviders.filter((p) => !p.configured),
      },
      {
        id: 'local',
        title: 'Local/self-hosted',
        description: 'Local, GCP-hosted, or self-managed provider endpoints.',
        providers: filteredProviders.filter(isLocalProvider),
      },
      {
        id: 'cloud',
        title: 'Cloud/API providers',
        description: 'Hosted API providers and managed model gateways.',
        providers: filteredProviders.filter(isCloudProvider),
      },
      {
        id: 'other',
        title: 'Other',
        description: 'Providers without a known category.',
        providers: filteredProviders.filter((p) => !isLocalProvider(p) && !isCloudProvider(p)),
      },
    ],
    [filteredProviders]
  );

  const selectedProvider = providerCtx.selectedProvider || (providers[0]?.name ?? '');
  const selectedModel = providerCtx.selectedModel || '';
  const selectedProviderModels = React.useMemo(() => {
    const models = providers.find((p) => p.name === selectedProvider)?.models;
    if (!Array.isArray(models)) return [] as string[];
    return models.filter((m): m is string => typeof m === 'string' && m.length > 0);
  }, [providers, selectedProvider]);

  const handleSavePreferences = async () => {
    setIsSaving(true);
    try {
      await apiClient.saveAccountPreferences({
        default_provider: selectedProvider,
        default_model: selectedModel,
      });
      showSuccess('Preferences saved', 'Your model preferences have been saved.');
    } catch {
      showError('Save failed', 'Could not save preferences. Please try again.');
    } finally {
      setIsSaving(false);
    }
  };

  const toggleProviderGroup = (groupId: ProviderGroupId) => {
    setOpenProviderGroups((current) =>
      current.includes(groupId) ? current.filter((id) => id !== groupId) : [...current, groupId]
    );
  };

  const toggleProviderDetails = (key: string) => {
    setExpandedProviderKey((current) => (current === key ? null : key));
  };

  if (providersLoading) {
    return (
      <PageState
        variant="loading"
        title="Loading settings"
        description="Pulling your providers and preferences."
        icon={<Loader2 className="h-6 w-6 animate-spin" />}
      />
    );
  }

  if (providersError) {
    return (
      <PageState
        variant="error"
        title="Settings unavailable"
        description={
          providersError instanceof Error
            ? providersError.message
            : 'We could not load your settings.'
        }
        actionLabel="Retry"
        onAction={() => {
          void refetch();
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-bg py-12 px-4">
      <Seo title="Settings" description="Provider and model settings." robots="noindex,nofollow" />
      <div className="max-w-6xl mx-auto">
        <div className="mb-12">
          <h1 className="text-4xl font-bold text-primary mb-3">Provider & Model Settings</h1>
          <p className="text-muted">Configure your AI provider API keys and model preferences</p>
        </div>

        <div className="mb-10">
          <Card variant="default" padding="md" className="mb-4 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-semibold text-text">Theme Mode</h2>
                <p className="text-sm text-muted">
                  Switch between dark, light, and high-contrast modes.
                </p>
              </div>
              <ContrastModeToggle />
            </div>
          </Card>
          <ThemePreview />
        </div>

        <div className="mb-10">
          <KeyboardShortcutsHelp />
        </div>

        {providers.length === 0 && (
          <InlineErrorState
            title="No providers configured"
            message="Add a provider key on the backend before saving model preferences."
            className="mb-8"
          />
        )}

        <Card variant="default" padding="md" className="mb-8 shadow-sm">
          <h2 className="text-xl font-semibold text-text mb-4">How to Configure API Keys</h2>
          <div className="space-y-3 text-text">
            <p>API keys should be set as environment variables on the backend server.</p>
            <div className="bg-bg rounded-lg p-4 font-mono text-sm text-primary">
              <div>export OPENAI_API_KEY=&quot;your-key-here&quot;</div>
              <div>export ANTHROPIC_API_KEY=&quot;your-key-here&quot;</div>
              <div>export GROQ_API_KEY=&quot;your-key-here&quot;</div>
              <div>export GOOGLE_API_KEY=&quot;your-key-here&quot;</div>
            </div>
            <p className="text-sm text-muted">
              For persistent configuration, add these to your{' '}
              <code className="bg-surface-hover px-2 py-1 rounded text-primary">.env</code> file or
              shell profile.
            </p>
          </div>
        </Card>

        <ProviderStatusSection
          filteredProviders={filteredProviders}
          providerGroups={providerGroups}
          providerSearch={providerSearch}
          setProviderSearch={setProviderSearch}
          openProviderGroups={openProviderGroups}
          toggleProviderGroup={toggleProviderGroup}
          expandedProviderKey={expandedProviderKey}
          toggleProviderDetails={toggleProviderDetails}
        />

        <ModelPreferencesSection
          providers={providers}
          selectedProvider={selectedProvider}
          selectedModel={selectedModel}
          selectedProviderModels={selectedProviderModels}
          isSaving={isSaving}
          onProviderChange={providerCtx.setSelectedProvider}
          onModelChange={providerCtx.setSelectedModel}
          onSave={handleSavePreferences}
        />
      </div>
    </div>
  );
};

export default SettingsPageContent;
