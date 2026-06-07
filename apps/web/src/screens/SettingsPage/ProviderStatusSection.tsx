import React from 'react';
import {
  Bot,
  Brain,
  Zap,
  Search,
  MessageSquare,
  Handshake,
  Wrench,
  Check,
  XCircle,
  ChevronDown,
  ChevronRight,
  Server,
} from 'lucide-react';
import { Badge, Card } from '../../components/ui';
import type { ProviderDisplay, ProviderGroup, ProviderGroupId } from './types';
import { isLocalProvider } from './providerUtils';

interface ProviderStatusSectionProps {
  filteredProviders: ProviderDisplay[];
  providerGroups: ProviderGroup[];
  providerSearch: string;
  setProviderSearch: (value: string) => void;
  openProviderGroups: ProviderGroupId[];
  toggleProviderGroup: (groupId: ProviderGroupId) => void;
  expandedProviderKey: string | null;
  toggleProviderDetails: (key: string) => void;
}

const ProviderIcon: React.FC<{ provider: ProviderDisplay }> = ({ provider }) => {
  if (provider.normalizedName.includes('openai'))
    return <Bot className="h-5 w-5 text-primary" />;
  if (provider.normalizedName.includes('anthropic'))
    return <Brain className="h-5 w-5 text-primary" />;
  if (provider.normalizedName.includes('groq')) return <Zap className="h-5 w-5 text-primary" />;
  if (
    provider.normalizedName.includes('google') ||
    provider.normalizedName.includes('gemini')
  )
    return <Search className="h-5 w-5 text-primary" />;
  if (provider.normalizedName.includes('cohere'))
    return <MessageSquare className="h-5 w-5 text-primary" />;
  if (provider.normalizedName.includes('together'))
    return <Handshake className="h-5 w-5 text-primary" />;
  if (isLocalProvider(provider)) return <Server className="h-5 w-5 text-primary" />;
  return <Wrench className="h-5 w-5 text-primary" />;
};

export const ProviderStatusSection: React.FC<ProviderStatusSectionProps> = ({
  filteredProviders,
  providerGroups,
  providerSearch,
  setProviderSearch,
  openProviderGroups,
  toggleProviderGroup,
  expandedProviderKey,
  toggleProviderDetails,
}) => (
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
                      <div key={providerKey} className="rounded-md border border-border bg-bg">
                        <button
                          type="button"
                          onClick={() => toggleProviderDetails(providerKey)}
                          className="flex w-full flex-col gap-3 p-3 text-left sm:flex-row sm:items-center sm:justify-between"
                          aria-expanded={expanded}
                          aria-label={`${provider.name} details in ${group.title}`}
                        >
                          <span className="flex items-center gap-3">
                            <span className="flex h-9 w-9 items-center justify-center rounded-md bg-surface-hover">
                              <ProviderIcon provider={provider} />
                            </span>
                            <span>
                              <span className="block font-medium text-text">{provider.name}</span>
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
                              <ChevronDown className="h-4 w-4 text-muted" aria-hidden="true" />
                            ) : (
                              <ChevronRight className="h-4 w-4 text-muted" aria-hidden="true" />
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
);
