import React from 'react';
import { Bot, Brain, Zap, Search, MessageSquare, Handshake, Wrench, Loader2, Check, Palette, Cpu, Sliders } from 'lucide-react';

type SettingsTab = 'appearance' | 'providers' | 'models';
const SETTINGS_TABS: { id: SettingsTab; label: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'providers', label: 'Providers', icon: Cpu },
  { id: 'models', label: 'Models', icon: Sliders },
];
import { useProviderSettings } from '../hooks/api/useSettings';
import ThemePreview from '../components/ThemePreview';
import KeyboardShortcutsHelp from '../components/KeyboardShortcutsHelp';
import Seo from '../components/Seo';
import { useProvider } from '../contexts/ProviderContext';
import { useToast } from '../contexts/ToastContext';
import { apiClient } from '@/api';
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
  enabled?: boolean;
  configured?: boolean;
  env_var?: string;
  api_key?: string;
  models?: unknown;
}

interface ProviderDisplay {
  name: string;
  configured: boolean;
  env_var?: string;
  models: string[];
}

const SettingsPageContent: React.FC = () => {
  const [activeTab, setActiveTab] = React.useState<SettingsTab>('appearance');
  const { data: providerData, isLoading: providersLoading, error: providersError, refetch } = useProviderSettings();
  const providerCtx = useProvider();
  const { showSuccess, showError } = useToast();
  const [isSaving, setIsSaving] = React.useState(false);

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
      configured: Boolean(p.enabled ?? p.configured ?? false),
      env_var: p.env_var || p.api_key ? `${name.toUpperCase()}_API_KEY` : undefined,
      models,
    };
  });
  const loading = providersLoading;

  const selectedProvider = providerCtx.selectedProvider || (providers[0]?.name ?? '');
  const selectedModel = providerCtx.selectedModel || '';
  const selectedProviderModels = React.useMemo(() => {
    const models = providers.find(p => p.name === selectedProvider)?.models;
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

  if (loading) {
    return <PageState variant="loading" title="Loading settings" description="Pulling your providers and preferences." icon={<Loader2 className="h-6 w-6 animate-spin" />} />;
  }

  if (providersError) {
    return (
      <PageState
        variant="error"
        title="Settings unavailable"
        description={providersError instanceof Error ? providersError.message : 'We could not load your settings.'}
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

      {/* Sticky tab header */}
      <div className="border-b border-border/60 bg-surface/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4">
          <div className="py-3"><h1 className="text-lg font-semibold text-text">Settings</h1></div>
          <div className="flex gap-1">
            {SETTINGS_TABS.map(({ id, label, icon: Icon }) => (
              <button key={id} type="button" onClick={() => setActiveTab(id)}
                className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === id ? 'border-primary text-primary' : 'border-transparent text-muted hover:text-text'
                }`}>
                <Icon className="w-3.5 h-3.5" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">

        {/* Appearance tab */}
        {activeTab === 'appearance' && (
          <>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-widest text-muted/70 mb-4">Theme</h2>
              <ThemePreview />
            </div>
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-widest text-muted/70 mb-4">Keyboard shortcuts</h2>
              <KeyboardShortcutsHelp />
            </div>
          </>
        )}

        {/* Providers tab */}
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
                <div>OPENAI_API_KEY="sk-…"</div>
                <div>ANTHROPIC_API_KEY="sk-ant-…"</div>
                <div>GROQ_API_KEY="gsk_…"</div>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {providers.map((provider) => (
                <Card key={provider.name} variant="default" padding="md" className="hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-text">{provider.name}</h3>
                    <Badge variant={provider.configured ? 'success' : 'danger'}>
                      {provider.configured ? 'Ready' : 'Missing'}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-center w-12 h-12 bg-surface-hover rounded-lg mb-3 mx-auto">
                    {provider.name === 'OpenAI' && <Bot className="w-6 h-6 text-primary" />}
                    {provider.name === 'Anthropic' && <Brain className="w-6 h-6 text-primary" />}
                    {provider.name === 'Groq' && <Zap className="w-6 h-6 text-primary" />}
                    {provider.name === 'Google' && <Search className="w-6 h-6 text-primary" />}
                    {provider.name === 'Cohere' && <MessageSquare className="w-6 h-6 text-primary" />}
                    {provider.name === 'Together' && <Handshake className="w-6 h-6 text-primary" />}
                    {!['OpenAI', 'Anthropic', 'Groq', 'Google', 'Cohere', 'Together'].includes(provider.name) && (
                      <Wrench className="w-6 h-6 text-primary" />
                    )}
                  </div>
                  {provider.env_var && (
                    <code className="block bg-bg px-2 py-1.5 rounded text-xs font-mono text-primary break-all mb-2">
                      {provider.env_var}
                    </code>
                  )}
                  {provider.models && provider.models.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {provider.models.slice(0, 3).map((model: string) => (
                        <Badge key={model} variant="primary" size="sm">{model}</Badge>
                      ))}
                    </div>
                  )}
                  <p className={`text-xs mt-3 pt-3 border-t border-border ${provider.configured ? 'text-success' : 'text-danger'}`}>
                    {provider.configured ? '✓ Ready to use' : '✗ Key not found'}
                  </p>
                </Card>
              ))}
            </div>
          </>
        )}

        {/* Models tab */}
        {activeTab === 'models' && (
          <Card variant="default" padding="md" className="shadow-sm">
            <h2 className="text-lg font-semibold text-text mb-1">Model Preferences</h2>
            <p className="text-sm text-muted mb-5">Configure default model settings and routing preferences.</p>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label htmlFor="default-provider" className="block text-sm font-medium text-text mb-2">Default Provider</label>
                <Select value={selectedProvider} onValueChange={providerCtx.setSelectedProvider}>
                  <SelectTrigger id="default-provider" className="w-full">
                    <SelectValue placeholder={providers.length === 0 ? 'auto' : undefined} />
                  </SelectTrigger>
                  <SelectContent>
                    {providers.length === 0 && <SelectItem value="auto">auto</SelectItem>}
                    {providers.map(p => <SelectItem key={p.name} value={p.name}>{p.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label htmlFor="default-model" className="block text-sm font-medium text-text mb-2">Default Model</label>
                <Select value={selectedModel} onValueChange={providerCtx.setSelectedModel}>
                  <SelectTrigger id="default-model" className="w-full">
                    <SelectValue placeholder="auto" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auto">auto</SelectItem>
                    {selectedProviderModels.map(model => <SelectItem key={model} value={model}>{model}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="mt-6">
              <Button
                type="button"
                onClick={handleSavePreferences}
                disabled={providers.length === 0}
                loading={isSaving}
                icon={!isSaving ? <Check className="w-4 h-4" /> : undefined}
              >
                {isSaving ? 'Saving…' : 'Save preferences'}
              </Button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
};

export default SettingsPageContent;
