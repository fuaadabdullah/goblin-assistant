import { Button } from '../../../../components/ui';
import { ProviderCardSkeleton } from '../../../../components/LoadingSkeleton';
import type { ProviderConfig } from '../../../../hooks/api/useSettings';
import type { ProviderStatusMap } from '../../../../hooks/useProviderStatus';
import type { DragEvent } from 'react';

const PROVIDER_SKELETON_KEYS = [
  'provider-skeleton-primary',
  'provider-skeleton-secondary',
  'provider-skeleton-tertiary',
] as const;

function healthDot(circuitState: string | undefined, isHealthy: boolean | undefined) {
  if (circuitState === 'hard_open')
    return (
      <span title="Hard-open (auth/billing issue)" className="text-xs text-error">
        ●
      </span>
    );
  if (circuitState === 'soft_open')
    return (
      <span title="Soft-open (probing)" className="text-xs text-warning">
        ◐
      </span>
    );
  if (isHealthy === true)
    return (
      <span title="Healthy" className="text-xs text-success">
        ●
      </span>
    );
  if (isHealthy === false)
    return (
      <span title="Unhealthy" className="text-xs text-error">
        ●
      </span>
    );
  return (
    <span title="Unknown" className="text-xs text-muted">
      ○
    </span>
  );
}

export default function ProviderSidebar({
  providers,
  isLoading,
  selectedProvider,
  onSelectProvider,
  onRefresh,
  routingStatus,
  showRoutingHealth,
  testingProviderName,
  onQuickTest,
  draggedProvider,
  isReordering,
  onDragStart,
  onDragOver,
  onDrop,
  providerStatuses,
  realtimeConnected,
}: {
  providers: ProviderConfig[];
  isLoading: boolean;
  selectedProvider: ProviderConfig | null;
  onSelectProvider: (provider: ProviderConfig) => void;
  onRefresh: () => void;
  routingStatus?: string;
  showRoutingHealth: boolean;
  testingProviderName: string | null;
  onQuickTest: (provider: ProviderConfig) => void;
  draggedProvider: ProviderConfig | null;
  isReordering: boolean;
  onDragStart: (provider: ProviderConfig) => void;
  onDragOver: (e: DragEvent<HTMLDivElement>) => void;
  onDrop: (provider: ProviderConfig) => void;
  providerStatuses?: ProviderStatusMap;
  realtimeConnected?: boolean;
}) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-text mb-3">Providers</h2>
        <p className="text-xs text-muted mb-4">
          Manage AI provider connections, priorities, and routing order
        </p>
      </div>

      {/* Quick Actions */}
      <div className="space-y-2">
        <Button
          variant="primary"
          size="sm"
          fullWidth
          icon="🔄"
          onClick={onRefresh}
          disabled={isLoading}
          loading={isLoading}
          aria-label="Refresh provider status"
        >
          Refresh Status
        </Button>
        <button
          type="button"
          className="w-full px-3 py-2 text-sm font-medium text-text bg-surface-hover rounded-lg hover:bg-surface-active transition-colors"
        >
          ➕ Add Provider
        </button>
      </div>

      {/* Routing Health */}
      {showRoutingHealth && (
        <div className="bg-surface rounded-lg p-3 border border-border">
          <h3 className="text-sm font-medium text-text mb-2">Routing Engine</h3>
          <div className="text-xs text-muted space-y-1">
            <div className="flex justify-between">
              <span>Status:</span>
              <span className="font-medium text-success">{routingStatus || 'Healthy'}</span>
            </div>
            <div className="flex justify-between">
              <span>Live feed:</span>
              <span className={realtimeConnected ? 'text-success' : 'text-muted'}>
                {realtimeConnected ? '● Realtime' : '○ Polling'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Provider List with Drag & Drop */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold text-text uppercase tracking-wide">
            Providers (Drag to Reorder)
          </h3>
          {isReordering && <span className="text-xs text-primary animate-pulse">Saving...</span>}
        </div>

        {isLoading ? (
          <div className="space-y-2" role="status" aria-label="Loading providers">
            {PROVIDER_SKELETON_KEYS.map((placeholderKey) => (
              <ProviderCardSkeleton key={placeholderKey} />
            ))}
            <span className="sr-only">Loading providers...</span>
          </div>
        ) : providers.length > 0 ? (
          providers.map((provider, index) => (
            <div
              key={provider.id || provider.name}
              draggable
              onDragStart={() => onDragStart(provider)}
              onDragOver={onDragOver}
              onDrop={() => onDrop(provider)}
              className={`cursor-move px-3 py-2 rounded-lg text-sm transition-all ${
                selectedProvider?.name === provider.name
                  ? 'bg-primary/20 text-primary border-2 border-primary'
                  : 'bg-surface border border-border hover:border-primary/50'
              } ${draggedProvider?.id === provider.id ? 'opacity-50' : ''}`}
            >
              <div className="flex items-center gap-2">
                <span className="text-muted text-xs font-mono">#{index + 1}</span>
                <button
                  type="button"
                  className="flex-1 font-medium text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary rounded-sm"
                  onClick={() => onSelectProvider(provider)}
                  aria-current={selectedProvider?.name === provider.name ? 'true' : undefined}
                  aria-label={`Select provider ${provider.name}`}
                >
                  {provider.name}
                </button>
                <div className="flex items-center gap-1">
                  {provider.priority && provider.priority <= 1 && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-info/20 text-info">
                      PRIMARY
                    </span>
                  )}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      onQuickTest(provider);
                    }}
                    disabled={testingProviderName === provider.name}
                    className="text-xs hover:text-success"
                    aria-label={`Test ${provider.name}`}
                  >
                    {testingProviderName === provider.name ? '🔄' : '🧪'}
                  </button>
                  {(() => {
                    const status = providerStatuses?.[provider.name];
                    return status ? (
                      healthDot(status.circuit_state, status.is_healthy)
                    ) : (
                      <span
                        className={`text-xs ${provider.enabled ? 'text-success' : 'text-muted'}`}
                      >
                        {provider.enabled ? '✓' : '○'}
                      </span>
                    );
                  })()}
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="text-xs text-muted">No providers configured</div>
        )}
      </div>
    </div>
  );
}
