import React from 'react';
import { Loader2, Palette, Cpu, Sliders } from 'lucide-react';
import { useProviderSettings } from '../../hooks/api/useSettings';
import ThemePreview from '../../components/ThemePreview';
import KeyboardShortcutsHelp from '../../components/KeyboardShortcutsHelp';
import ContrastModeToggle from '../../components/ContrastModeToggle';
import Seo from '../../components/Seo';
import { useProvider } from '../../contexts/ProviderContext';
import { useToast } from '../../hooks/useToast';
import { apiClient } from '@/lib/api';
import { getUserMessage } from '@/lib/error/toast';
import { InlineErrorState, PageState } from '../../components/ui';
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

type SettingsTab = 'appearance' | 'providers' | 'models';

const SETTINGS_TABS: { id: SettingsTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'providers', label: 'Providers', icon: Cpu },
  { id: 'models', label: 'Models', icon: Sliders },
];

const SettingsPageContent: React.FC = () => {
  const [activeTab, setActiveTab] = React.useState<SettingsTab>('appearance');
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
    } catch (error) {
      showError('Save failed', getUserMessage(error));
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
    <div className="min-h-screen bg-bg">
      <Seo title="Settings" description="Provider and model settings." robots="noindex,nofollow" />

      <div className="border-b border-border/60 bg-surface/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4">
          <div className="py-3"><h1 className="text-lg font-semibold text-text">Settings</h1></div>
          <div className="flex gap-1">
            {SETTINGS_TABS.map(({ id, label, icon: Icon }) => (
              <button key={id} type="button" onClick={() => setActiveTab(id)}
                className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === id ? 'border-primary text-primary' : 'border-transparent text-muted hover:text-text'}`}>
                <Icon className="w-3.5 h-3.5" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {activeTab === 'appearance' && (
          <>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-widest text-muted/70 mb-4">Theme</h2>
              <ThemePreview />
            </div>
            <div className="rounded-xl border border-border bg-surface px-5 py-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm font-medium text-text">High-contrast mode</p>
                <p className="text-xs text-muted mt-0.5">Increases contrast for better readability.</p>
              </div>
              <ContrastModeToggle />
            </div>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-widest text-muted/70 mb-4">Keyboard shortcuts</h2>
              <KeyboardShortcutsHelp />
            </div>
          </>
        )}

        {activeTab === 'providers' && (
          <>
            {providers.length === 0 && (
              <InlineErrorState
                title="No providers configured"
                message="Add a provider API key on the backend before saving model preferences."
                className="mb-4"
              />
            )}
            <div className="rounded-xl border border-border bg-surface px-5 py-4">
              <h2 className="text-sm font-medium text-text mb-1">API key setup</h2>
              <p className="text-xs text-muted mb-3">Set provider keys as environment variables on the backend server.</p>
              <div className="bg-bg rounded-lg px-4 py-3 font-mono text-xs text-primary space-y-1">
                <div>OPENAI_API_KEY=&quot;sk-…&quot;</div>
                <div>ANTHROPIC_API_KEY=&quot;sk-ant-…&quot;</div>
                <div>GROQ_API_KEY=&quot;gsk_…&quot;</div>
              </div>
            </div>
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
          </>
        )}

        {activeTab === 'models' && (
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
        )}
      </div>
    </div>
  );
};

export default SettingsPageContent;
