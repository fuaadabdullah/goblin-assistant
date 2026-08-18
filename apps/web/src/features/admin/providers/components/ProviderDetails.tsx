import type { ProviderConfig } from '../../../../hooks/api/useSettings';
import { useRoutingProviders } from '../hooks/useRoutingAnalytics';

interface RoutingStats {
  ewma_latency_ms: number;
  p95_latency_ms: number;
  success_rate: number;
  total_cost_usd: number;
  ewma_tokens_per_sec: number;
  total_output_tokens: number;
}

function getCircuitStateColor(state?: string): string {
  switch (state?.toLowerCase()) {
    case 'closed':
      return 'bg-success/20 text-success border border-success/30';
    case 'soft_open':
      return 'bg-warning/20 text-warning border border-warning/30';
    case 'hard_open':
      return 'bg-danger/20 text-danger border border-danger/30';
    default:
      return 'bg-muted/20 text-muted border border-muted/30';
  }
}

export default function ProviderDetails({
  provider,
  onSetPriority,
}: {
  provider: ProviderConfig;
  onSetPriority: (providerId: number, priority: number, role?: 'primary' | 'fallback') => void;
}) {
  const { data: routingData } = useRoutingProviders();

  const routingStats: RoutingStats | null =
    routingData?.providers?.[provider.name]?.routing_stats || null;
  const health = routingData?.providers?.[provider.name]?.health;

  return (
    <div className="bg-surface rounded-xl shadow-sm border border-border p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-semibold text-text">{provider.name}</h2>
          <p className="text-sm text-muted">Provider Configuration & Testing</p>
        </div>
      </div>

      {/* Status Metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <div className="bg-bg rounded-lg p-4">
          <div className="text-xs text-muted mb-1">Status</div>
          <div
            className={`text-lg font-semibold ${provider.enabled ? 'text-success' : 'text-muted'}`}
          >
            {provider.enabled ? 'Enabled' : 'Disabled'}
          </div>
        </div>
        <div className="bg-bg rounded-lg p-4">
          <div className="text-xs text-muted mb-1">Priority</div>
          <div className="text-lg font-semibold text-text">{provider.priority || 'N/A'}</div>
        </div>
        <div className="bg-bg rounded-lg p-4">
          <div className="text-xs text-muted mb-1">Weight</div>
          <div className="text-lg font-semibold text-text">{provider.weight || 1.0}</div>
        </div>
        <div className="bg-bg rounded-lg p-4">
          <div className="text-xs text-muted mb-1">Models</div>
          <div className="text-lg font-semibold text-text">{provider.models?.length || 0}</div>
        </div>
      </div>

      {/* Live Routing Metrics */}
      {routingStats && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-text mb-3">Live Routing Metrics</h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="bg-bg rounded-lg p-3">
              <div className="text-xs text-muted mb-1">Avg Latency (EWMA)</div>
              <div className="text-base font-semibold text-text">
                {routingStats.ewma_latency_ms.toFixed(0)}ms
              </div>
            </div>
            <div className="bg-bg rounded-lg p-3">
              <div className="text-xs text-muted mb-1">P95 Latency</div>
              <div className="text-base font-semibold text-text">
                {routingStats.p95_latency_ms.toFixed(0)}ms
              </div>
            </div>
            <div className="bg-bg rounded-lg p-3">
              <div className="text-xs text-muted mb-1">Success Rate</div>
              <div className="text-base font-semibold text-success">
                {(routingStats.success_rate * 100).toFixed(1)}%
              </div>
            </div>
            <div className="bg-bg rounded-lg p-3">
              <div className="text-xs text-muted mb-1">Hour Cost</div>
              <div className="text-base font-semibold text-text">
                ${routingStats.total_cost_usd.toFixed(4)}
              </div>
            </div>
            <div className="bg-bg rounded-lg p-3">
              <div className="text-xs text-muted mb-1">Throughput</div>
              <div className="text-base font-semibold text-text">
                {routingStats.ewma_tokens_per_sec.toFixed(0)} tok/s
              </div>
            </div>
            <div className="bg-bg rounded-lg p-3">
              <div className="text-xs text-muted mb-1">Total Tokens</div>
              <div className="text-base font-semibold text-text">
                {routingStats.total_output_tokens.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Circuit State */}
      {health && (
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-text mb-2">Circuit Breaker State</h3>
          <div
            className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium ${getCircuitStateColor(health.status)}`}
          >
            <span className="w-2 h-2 rounded-full bg-current" />
            {health.status?.toUpperCase() || 'UNKNOWN'}
          </div>
        </div>
      )}

      {/* Priority Actions */}
      <div className="flex gap-2 mb-6 flex-wrap">
        <button
          type="button"
          onClick={() => provider.id && onSetPriority(provider.id, 1, 'primary')}
          disabled={!provider.id}
          className="px-4 py-2 bg-info text-text-inverse rounded-lg hover:bg-info/90 transition-colors text-sm font-medium shadow-glow-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          🏆 Set as Primary
        </button>
        <button
          type="button"
          onClick={() => provider.id && onSetPriority(provider.id, 10, 'fallback')}
          disabled={!provider.id}
          className="px-4 py-2 bg-warning text-text-inverse rounded-lg hover:bg-warning/90 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          🛡️ Set as Fallback
        </button>
      </div>

      {/* Configuration Details */}
      <div className="space-y-3">
        <div>
          <label htmlFor="provider-base-url" className="block text-xs font-medium text-text mb-1">
            Base URL
          </label>
          <input
            id="provider-base-url"
            type="text"
            value={provider.base_url || 'Not configured'}
            readOnly
            className="w-full px-3 py-2 border border-border rounded-lg bg-surface-hover text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-text mb-1">API Key Status</label>
          <div
            className={`px-3 py-2 border rounded-lg text-sm ${
              provider.api_key
                ? 'border-success bg-success/20 text-success'
                : 'border-danger bg-danger/20 text-danger'
            }`}
          >
            {provider.api_key ? '✓ Configured' : '✗ Not configured'}
          </div>
        </div>
      </div>
    </div>
  );
}
