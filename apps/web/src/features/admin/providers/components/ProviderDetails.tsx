import type { ProviderConfig } from '../../../../hooks/api/useSettings';

export default function ProviderDetails({
  provider,
  onSetPriority,
}: {
  provider: ProviderConfig;
  onSetPriority: (providerId: number, priority: number, role?: 'primary' | 'fallback') => void;
}) {
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
            className={`text-lg font-semibold ${
              provider.enabled ? 'text-success' : 'text-muted'
            }`}
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
          <label
            htmlFor="provider-base-url"
            className="block text-xs font-medium text-text mb-1"
          >
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

