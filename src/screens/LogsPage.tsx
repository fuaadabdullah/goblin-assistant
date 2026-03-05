import { useState, useEffect } from 'react';
import TwoColumnLayout from '../components/TwoColumnLayout';
import { apiClient } from '../api/apiClient';
import { Button, Alert } from '../components/ui';
import { ListSkeleton } from '../components/LoadingSkeleton';

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'warning' | 'error' | 'debug';
  service: string;
  message: string;
  details?: unknown;
}

/**
 * Debug/Event Log: Recent backend errors, failed requests, and system events
 */
const LogsPageContent = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<'all' | 'error' | 'warning' | 'info'>('all');
  const [serviceFilter, setServiceFilter] = useState<string>('all');
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadLogs();
  }, []);

  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(loadLogs, 5000); // Refresh every 5s
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const loadLogs = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const logsData = await apiClient.getRaptorLogs(100);
      const raw = logsData?.log_tail ?? '';
      const lines = raw
        .split('\n')
        .map(line => line.trim())
        .filter(Boolean);

      const transformedLogs: LogEntry[] = lines.map((line, index) => {
        try {
          const parsed = JSON.parse(line) as any;
          return {
            id: parsed.id || `log-${index}`,
            timestamp: parsed.timestamp || new Date().toISOString(),
            level: parsed.level || 'info',
            service: parsed.service || parsed.source || 'raptor',
            message: parsed.message || parsed.msg || line,
            details: parsed.details || parsed.metadata || parsed.context,
          } satisfies LogEntry;
        } catch {
          return {
            id: `log-${index}`,
            timestamp: new Date().toISOString(),
            level: 'info',
            service: 'raptor',
            message: line,
          };
        }
      });

      setLogs(transformedLogs);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load logs';
      setError(errorMessage);
      console.error('Failed to load logs:', err);

      // Optionally show empty state instead of keeping old data
      setLogs([]);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredLogs = logs.filter(log => {
    if (filter !== 'all' && log.level !== filter) return false;
    if (serviceFilter !== 'all' && log.service !== serviceFilter) return false;
    return true;
  });

  const services = ['all', ...Array.from(new Set(logs.map(log => log.service)))];

  const levelColors = {
    error: { bg: 'bg-danger/20', text: 'text-danger', dot: 'bg-danger' },
    warning: { bg: 'bg-warning/20', text: 'text-warning', dot: 'bg-warning' },
    info: { bg: 'bg-info/20', text: 'text-info', dot: 'bg-info' },
    debug: { bg: 'bg-surface-hover', text: 'text-muted', dot: 'bg-muted' },
  };

  const sidebar = (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-text mb-3">Logs & Events</h2>
        <p className="text-xs text-muted mb-4">
          Backend errors, failed requests, and system events
        </p>
      </div>

      {/* Filters */}
      <div>
        <label className="block text-xs font-medium text-text mb-2">Level Filter</label>
        <select
          value={filter}
          onChange={e => setFilter(e.target.value as any)}
          className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-surface-hover focus:ring-2 focus:ring-primary"
          aria-label="Log level filter"
        >
          <option value="all">All Levels</option>
          <option value="error">Errors Only</option>
          <option value="warning">Warnings Only</option>
          <option value="info">Info Only</option>
        </select>
      </div>

      <div>
        <label className="block text-xs font-medium text-text mb-2">Service Filter</label>
        <select
          value={serviceFilter}
          onChange={e => setServiceFilter(e.target.value)}
          className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-surface-hover focus:ring-2 focus:ring-primary"
          aria-label="Service filter"
        >
          {services.map(service => (
            <option key={service} value={service}>
              {service.charAt(0).toUpperCase() + service.slice(1)}
            </option>
          ))}
        </select>
      </div>

      {/* Auto-refresh Toggle */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="auto-refresh"
          checked={autoRefresh}
          onChange={e => setAutoRefresh(e.target.checked)}
          className="rounded border-border text-primary focus:ring-primary"
        />
        <label htmlFor="auto-refresh" className="text-xs text-text">
          Auto-refresh (5s)
        </label>
      </div>

      {/* Quick Actions */}
      <div className="space-y-2">
        <Button
          variant="primary"
          size="sm"
          fullWidth
          icon="🔄"
          onClick={loadLogs}
          disabled={isLoading}
          loading={isLoading}
          aria-label="Refresh logs"
        >
          Refresh Logs
        </Button>
        <Button
          variant="danger"
          size="sm"
          fullWidth
          icon="🗑️"
          onClick={() => setLogs([])}
          aria-label="Clear logs display"
        >
          Clear Display
        </Button>
      </div>

      {/* Log Stats */}
      <div className="bg-surface rounded-lg p-3 border border-border">
        <h3 className="text-sm font-medium text-text mb-2">Statistics</h3>
        <div className="space-y-1 text-xs">
          <div className="flex justify-between">
            <span className="text-muted">Total:</span>
            <span className="font-medium">{logs.length}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-danger">Errors:</span>
            <span className="font-medium">{logs.filter(l => l.level === 'error').length}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-warning">Warnings:</span>
            <span className="font-medium">{logs.filter(l => l.level === 'warning').length}</span>
          </div>
        </div>
      </div>
    </div>
  );

  const mainContent = (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text mb-2">System Logs</h1>
        <p className="text-muted">
          Real-time monitoring of backend errors, warnings, and system events
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <Alert
          variant="danger"
          title="Failed to Load Logs"
          message={
            <>
              <p className="mb-3">{error}</p>
              <Button
                variant="danger"
                size="sm"
                icon="🔄"
                onClick={() => {
                  setError(null);
                  loadLogs();
                }}
                aria-label="Retry loading logs"
              >
                Retry
              </Button>
            </>
          }
          dismissible
          onDismiss={() => setError(null)}
        />
      )}

      {/* Loading State */}
      {isLoading && <ListSkeleton count={8} />}

      {/* Live region for auto-refresh updates */}
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {!isLoading &&
          logs.length > 0 &&
          `Logs updated. Showing ${filteredLogs.length} of ${logs.length} entries`}
      </div>

      {/* Log Entries */}
      {!isLoading && (
        <div className="space-y-3">
          {filteredLogs.length > 0 ? (
            filteredLogs.map(log => {
              const colors = levelColors[log.level];
              const isSelected = selectedLog?.id === log.id;
              const detailsId = `log-details-${log.id}`;

              return (
                <article
                  key={log.id}
                  className={`bg-surface rounded-lg shadow-sm border border-border p-4 transition-shadow ${
                    isSelected ? 'ring-2 ring-primary' : 'hover:shadow-md'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() =>
                      setSelectedLog(isSelected ? null : log)
                    }
                    className="w-full text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary rounded"
                    aria-expanded={isSelected}
                    aria-controls={detailsId}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}
                        >
                          <span
                            className={`inline-block w-2 h-2 rounded-full ${colors.dot} mr-2`}
                            aria-hidden="true"
                          ></span>
                          {log.level.toUpperCase()}
                        </span>
                        <span className="px-3 py-1 bg-surface-hover text-text rounded-full text-xs font-medium">
                          {log.service}
                        </span>
                      </div>
                      <span className="text-xs text-muted font-mono">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-text font-medium mb-2">{log.message}</p>
                  </button>
                  {isSelected && log.details != null && (
                    <div className="mt-3 pt-3 border-t border-border" id={detailsId}>
                      <h4 className="text-xs font-semibold text-text mb-2">Details:</h4>
                      <pre className="text-xs bg-bg p-3 rounded border border-border overflow-x-auto">
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    </div>
                  )}
                </article>
              );
            })
          ) : (
            <div className="bg-surface rounded-xl shadow-sm border border-border p-12 text-center">
              <div className="text-6xl mb-4" aria-hidden="true">📋</div>
              <h3 className="text-lg font-medium text-text mb-2">No Logs Found</h3>
              <p className="text-muted">
                {filter !== 'all' || serviceFilter !== 'all'
                  ? 'Try adjusting your filters'
                  : 'System logs will appear here'}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );

  return <TwoColumnLayout sidebar={sidebar}>{mainContent}</TwoColumnLayout>;
};

export default LogsPageContent;
