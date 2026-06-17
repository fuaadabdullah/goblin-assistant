import { useRoutingAudit } from '../hooks/useRoutingAnalytics';

export default function RoutingAuditTab({ providerId }: { providerId?: string }) {
  const { data, isLoading } = useRoutingAudit(50);

  const records = data?.records || [];
  const filteredRecords = providerId
    ? records.filter(
        (r) =>
          r.selected_provider === providerId ||
          r.provider_id === providerId ||
          r.attempted_providers?.includes(providerId)
      )
    : records;

  const formatTime = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="bg-surface rounded-xl shadow-sm border border-border p-6">
        <div className="text-center text-muted">Loading routing audit...</div>
      </div>
    );
  }

  if (filteredRecords.length === 0) {
    return (
      <div className="bg-surface rounded-xl shadow-sm border border-border p-6">
        <div className="text-center text-muted">No routing records found</div>
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-xl shadow-sm border border-border overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-bg border-b border-border">
            <tr>
              <th className="text-left px-4 py-3 font-semibold text-text">Time</th>
              <th className="text-left px-4 py-3 font-semibold text-text">Request ID</th>
              <th className="text-left px-4 py-3 font-semibold text-text">Event</th>
              <th className="text-left px-4 py-3 font-semibold text-text">Model</th>
              <th className="text-left px-4 py-3 font-semibold text-text">Selected</th>
              <th className="text-left px-4 py-3 font-semibold text-text">Attempted</th>
              <th className="text-right px-4 py-3 font-semibold text-text">Latency (ms)</th>
              <th className="text-right px-4 py-3 font-semibold text-text">Cost ($)</th>
              <th className="text-right px-4 py-3 font-semibold text-text">Tokens</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filteredRecords.map((record, idx) => (
              <tr key={`${record.request_id}-${idx}`} className="hover:bg-bg/50 transition-colors">
                <td className="px-4 py-3 text-muted text-xs whitespace-nowrap">
                  {formatTime(record.timestamp)}
                </td>
                <td className="px-4 py-3 text-text text-xs font-mono">
                  {record.request_id.substring(0, 8)}...
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-1 rounded text-xs font-medium ${
                      record.event === 'outcome'
                        ? 'bg-success/20 text-success'
                        : 'bg-info/20 text-info'
                    }`}
                  >
                    {record.event}
                  </span>
                </td>
                <td className="px-4 py-3 text-text text-xs">{record.model || '—'}</td>
                <td className="px-4 py-3 text-text text-xs font-medium">
                  {record.selected_provider || record.provider_id || '—'}
                </td>
                <td className="px-4 py-3 text-text text-xs">
                  {record.attempted_providers ? record.attempted_providers.join(', ') : '—'}
                </td>
                <td className="px-4 py-3 text-right text-text text-xs font-mono">
                  {record.latency_ms ? record.latency_ms.toFixed(0) : '—'}
                </td>
                <td className="px-4 py-3 text-right text-text text-xs font-mono">
                  {record.cost_usd ? record.cost_usd.toFixed(6) : '—'}
                </td>
                <td className="px-4 py-3 text-right text-text text-xs font-mono">
                  {record.input_tokens && record.output_tokens
                    ? (record.input_tokens + record.output_tokens).toLocaleString()
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="bg-bg border-t border-border px-4 py-2 text-xs text-muted">
        Showing {filteredRecords.length} of {records.length} records (auto-refresh every 10s)
      </div>
    </div>
  );
}
