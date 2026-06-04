import React from 'react';
import {
  Bot,
  Brain,
  Zap,
  Search,
  MessageSquare,
  Handshake,
  Wrench,
  Loader2,
  Check,
  XCircle,
  ChevronDown,
  ChevronRight,
  Server,
} from 'lucide-react';
import { useProviderSettings } from '../hooks/api/useSettings';
import ThemePreview from '../components/ThemePreview';
import KeyboardShortcutsHelp from '../components/KeyboardShortcutsHelp';
import ContrastModeToggle from '../components/ContrastModeToggle';
import Seo from '../components/Seo';
import { useProvider } from '../contexts/ProviderContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '@/lib/api';
import {
  Button,
  Badge,
  Card,
  InlineErrorState,
  PageState,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui';

interface ProviderSource {
  name?: string;
  id?: number;
  enabled?: boolean;
  configured?: boolean;
  env_var?: string;
  api_key?: string;
  base_url?: string;
  models?: unknown;
}

interface ProviderDisplay {
  name: string;
  normalizedName: string;
  configured: boolean;
  env_var?: string;
  base_url?: string;
  models: string[];
}

type ProviderGroupId = 'configured' | 'needs-setup' | 'local' | 'cloud' | 'other';

interface ProviderGroup {
  id: ProviderGroupId;
  title: string;
  description: string;
  providers: ProviderDisplay[];
}

const DEFAULT_OPEN_PROVIDER_GROUPS: ProviderGroupId[] = ['configured', 'needs-setup'];

const LOCAL_PROVIDER_HINTS = ['ollama', 'llamacpp', 'colab', 'local', 'gcp', 'mock'];

const CLOUD_PROVIDER_HINTS = [
  'openai',
  'anthropic',
  'groq',
  'gemini',
  'google',
  'deepseek',
  'siliconeflow',
  'azure',
  'vertex',
  'aliyun',
  'together',
  'replicate',
  'huggingface',
  'cohere',
];

const normalizeProviderName = (name: string) => name.toLowerCase().replace(/\s+/g, '_');

const providerMatchesSearch = (provider: ProviderDisplay, query: string) => {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return true;
  return [
    provider.name,
    provider.normalizedName,
    provider.env_var ?? '',
    provider.base_url ?? '',
    ...provider.models,
  ]
    .join(' ')
    .toLowerCase()
    .includes(normalizedQuery);
};

const isLocalProvider = (provider: ProviderDisplay) =>
  LOCAL_PROVIDER_HINTS.some((hint) => provider.normalizedName.includes(hint));

const isCloudProvider = (provider: ProviderDisplay) =>
  CLOUD_PROVIDER_HINTS.some((hint) => provider.normalizedName.includes(hint));

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
    if (Array.isArray(providerData)) {
      return providerData as ProviderSource[];
    }

    if (providerData && typeof providerData === 'object') {
      const maybeProviders = (providerData as { providers?: unknown }).providers;
      if (Array.isArray(maybeProviders)) {
        return maybeProviders as ProviderSource[];
      }

      return Object.entries(providerData as Record<string, unknown>).map(([name, raw]) => {
        if (raw && typeof raw === 'object') {
          return {
            name,
            ...(raw as ProviderSource),
          };
        }

        return { name };
      });
    }

    return [];
  }, [providerData]);

  // Adapt provider data shape: backend may return keys with different naming (configured/env_var)
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
  const loading = providersLoading;

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
        providers: filteredProviders.filter((provider) => provider.configured),
      },
      {
        id: 'needs-setup',
        title: 'Needs setup',
        description: 'Missing credentials or disabled in the provider registry.',
        providers: filteredProviders.filter((provider) => !provider.configured),
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
        providers: filteredProviders.filter(
          (provider) => !isLocalProvider(provider) && !isCloudProvider(provider)
        ),
      },
    ],
    [filteredProviders]
  );

  const selectedProvider = providerCtx.selectedProvider || (providers[0]?.name ?? '');
  const selectedModel = providerCtx.selectedModel || '';
  const selectedProviderModels = React.useMemo(() => {
    const models = providers.find((p) => p.name === selectedProvider)?.models;
    if (!Array.isArray(models)) {
      return [] as string[];
    }
    return models.filter((model): model is string => typeof model === 'string' && model.length > 0);
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

  if (loading) {
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
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-4xl font-bold text-primary mb-3">Provider & Model Settings</h1>
          <p className="text-muted">Configure your AI provider API keys and model preferences</p>
        </div>

        {/* Theme Preview + Palette Switcher */}
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

        {/* Keyboard Shortcuts */}
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

        {/* Environment Variables Instructions */}
        <Card variant="default" padding="md" className="mb-8 shadow-sm">
          <h2 className="text-xl font-semibold text-text mb-4">How to Configure API Keys</h2>
          <div className="space-y-3 text-text">
            <p>API keys should be set as environment variables on the backend server.</p>
            <div className="bg-bg rounded-lg p-4 font-mono text-sm text-primary">
              <div>export OPENAI_API_KEY="your-key-here"</div>
              <div>export ANTHROPIC_API_KEY="your-key-here"</div>
              <div>export GROQ_API_KEY="your-key-here"</div>
              <div>export GOOGLE_API_KEY="your-key-here"</div>
            </div>
            <p className="text-sm text-muted">
              For persistent configuration, add these to your{' '}
              <code className="bg-surface-hover px-2 py-1 rounded text-primary">.env</code> file or
              shell profile.
            </p>
          </div>
        </Card>

        {/* Provider Status Cards */}
        <div>
          <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-text">Provider Status</h2>
              <p className="text-sm text-muted">
                Search and inspect providers without scanning the full registry at once.
              </p>
            </div>
            <label className="relative block md:w-80">
              <span className="sr-only">Search providers</span>
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted" />
              <input
                type="search"
                value={providerSearch}
                onChange={(event) => setProviderSearch(event.target.value)}
                placeholder="Search providers, env vars, models..."
                className="w-full rounded-md border border-border bg-surface py-2 pl-9 pr-3 text-sm text-text placeholder:text-muted focus:border-primary focus:outline-none"
              />
            </label>
          </div>

          {filteredProviders.length === 0 && (
            <Card variant="default" padding="md" className="text-sm text-muted">
              No providers match this search.
            </Card>
          )}

          <div className="space-y-3">
            {providerGroups.map((group) => {
              const isOpen = openProviderGroups.includes(group.id);
              return (
                <Card key={group.id} variant="default" padding="none" className="overflow-hidden">
                  <button
                    type="button"
                    onClick={() => toggleProviderGroup(group.id)}
                    className="flex w-full items-center justify-between gap-3 p-4 text-left hover:bg-surface-hover"
                    aria-expanded={isOpen}
                    aria-label={`Toggle ${group.title} providers`}
                  >
                    <span>
                      <span className="flex items-center gap-2 text-base font-semibold text-text">
                        {isOpen ? (
                          <ChevronDown className="h-4 w-4 text-muted" aria-hidden="true" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-muted" aria-hidden="true" />
                        )}
                        {group.title}
                      </span>
                      <span className="mt-1 block text-sm text-muted">{group.description}</span>
                    </span>
                    <Badge variant={group.providers.length > 0 ? 'primary' : 'secondary'}>
                      {group.providers.length}
                    </Badge>
                  </button>
                  {isOpen && (
                    <div className="space-y-2 border-t border-border p-3">
                      {group.providers.length === 0 ? (
                        <div className="rounded-md bg-bg p-3 text-sm text-muted">
                          No providers in this group.
                        </div>
                      ) : (
                        group.providers.map((provider) => {
                          const providerKey = `${group.id}:${provider.name}`;
                          const expanded = expandedProviderKey === providerKey;
                          return (
                            <div
                              key={providerKey}
                              className="rounded-md border border-border bg-bg"
                            >
                              <button
                                type="button"
                                onClick={() => toggleProviderDetails(providerKey)}
                                className="flex w-full flex-col gap-3 p-3 text-left sm:flex-row sm:items-center sm:justify-between"
                                aria-expanded={expanded}
                                aria-label={`${provider.name} details in ${group.title}`}
                              >
                                <span className="flex items-center gap-3">
                                  <span className="flex h-9 w-9 items-center justify-center rounded-md bg-surface-hover">
                                    {provider.normalizedName.includes('openai') && (
                                      <Bot className="h-5 w-5 text-primary" />
                                    )}
                                    {provider.normalizedName.includes('anthropic') && (
                                      <Brain className="h-5 w-5 text-primary" />
                                    )}
                                    {provider.normalizedName.includes('groq') && (
                                      <Zap className="h-5 w-5 text-primary" />
                                    )}
                                    {(provider.normalizedName.includes('google') ||
                                      provider.normalizedName.includes('gemini')) && (
                                      <Search className="h-5 w-5 text-primary" />
                                    )}
                                    {provider.normalizedName.includes('cohere') && (
                                      <MessageSquare className="h-5 w-5 text-primary" />
                                    )}
                                    {provider.normalizedName.includes('together') && (
                                      <Handshake className="h-5 w-5 text-primary" />
                                    )}
                                    {isLocalProvider(provider) && (
                                      <Server className="h-5 w-5 text-primary" />
                                    )}
                                    {!provider.normalizedName.includes('openai') &&
                                      !provider.normalizedName.includes('anthropic') &&
                                      !provider.normalizedName.includes('groq') &&
                                      !provider.normalizedName.includes('google') &&
                                      !provider.normalizedName.includes('gemini') &&
                                      !provider.normalizedName.includes('cohere') &&
                                      !provider.normalizedName.includes('together') &&
                                      !isLocalProvider(provider) && (
                                        <Wrench className="h-5 w-5 text-primary" />
                                      )}
                                  </span>
                                  <span>
                                    <span className="block font-medium text-text">
                                      {provider.name}
                                    </span>
                                    <span className="block text-xs text-muted">
                                      {provider.models.length} model
                                      {provider.models.length === 1 ? '' : 's'}
                                      {provider.env_var ? ` · ${provider.env_var}` : ''}
                                    </span>
                                  </span>
                                </span>
                                <span className="flex items-center gap-2">
                                  <Badge variant={provider.configured ? 'success' : 'danger'}>
                                    {provider.configured ? 'Configured' : 'Missing'}
                                  </Badge>
                                  {expanded ? (
                                    <ChevronDown
                                      className="h-4 w-4 text-muted"
                                      aria-hidden="true"
                                    />
                                  ) : (
                                    <ChevronRight
                                      className="h-4 w-4 text-muted"
                                      aria-hidden="true"
                                    />
                                  )}
                                </span>
                              </button>
                              {expanded && (
                                <div className="border-t border-border p-3">
                                  <div className="flex items-center gap-2 text-xs text-muted">
                                    {provider.configured ? (
                                      <Check className="h-4 w-4 text-success" aria-hidden="true" />
                                    ) : (
                                      <XCircle className="h-4 w-4 text-danger" aria-hidden="true" />
                                    )}
                                    <span>
                                      {provider.configured
                                        ? 'API key detected and ready to use'
                                        : 'API key not found. Configure on backend.'}
                                    </span>
                                  </div>
                                  {provider.env_var && (
                                    <code className="mt-3 block rounded bg-surface px-3 py-2 text-xs font-mono text-primary">
                                      {provider.env_var}
                                    </code>
                                  )}
                                  {provider.models.length > 0 && (
                                    <div className="mt-3 flex flex-wrap gap-1">
                                      {provider.models.map((model) => (
                                        <Badge key={model} variant="primary" size="sm">
                                          {model}
                                        </Badge>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })
                      )}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </div>

        {/* Model Preferences */}
        <Card variant="default" padding="md" className="mt-12 shadow-sm">
          <h2 className="text-xl font-semibold text-text mb-4">Model Preferences</h2>
          <p className="text-muted mb-4">
            Configure default model settings and routing preferences.
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label
                htmlFor="default-provider"
                className="block text-sm font-medium text-text mb-2"
              >
                Default Provider
              </label>
              <Select value={selectedProvider} onValueChange={providerCtx.setSelectedProvider}>
                <SelectTrigger id="default-provider" className="w-full">
                  <SelectValue placeholder={providers.length === 0 ? 'auto' : undefined} />
                </SelectTrigger>
                <SelectContent>
                  {providers.length === 0 && <SelectItem value="auto">auto</SelectItem>}
                  {providers.map((p) => (
                    <SelectItem key={p.name} value={p.name}>
                      {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label htmlFor="default-model" className="block text-sm font-medium text-text mb-2">
                Default Model
              </label>
              <Select value={selectedModel} onValueChange={providerCtx.setSelectedModel}>
                <SelectTrigger id="default-model" className="w-full">
                  <SelectValue placeholder="auto" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">auto</SelectItem>
                  {selectedProviderModels.map((model) => (
                    <SelectItem key={model} value={model}>
                      {model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="mt-6 flex items-center gap-3">
            <Button
              type="button"
              onClick={handleSavePreferences}
              disabled={providers.length === 0}
              loading={isSaving}
              icon={!isSaving ? <Check className="w-4 h-4" /> : undefined}
            >
              {isSaving ? 'Saving...' : 'Save preferences'}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default SettingsPageContent;
