import { useEffect, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import TwoColumnLayout from '../components/TwoColumnLayout';
import { apiClient } from '../lib/api';
import { queryKeys } from '../lib/query-keys';
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

interface RaptorLogsPayload {
  log_tail?: string;
}

type LogFilter = 'all' | 'error' | 'warning' | 'info';

const levelColors: Record<LogEntry['level'], { bg: string; text: string; dot: string }> = {
  error: { bg: 'bg-danger/20', text: 'text-danger', dot: 'bg-danger' },
  warning: { bg: 'bg-warning/20', text: 'text-warning', dot: 'bg-warning' },
  info: { bg: 'bg-info/20', text: 'text-info', dot: 'bg-info' },
  debug: { bg: 'bg-surface-hover', text: 'text-muted', dot: 'bg-muted' },
};

function isLogFilter(value: string): value is LogFilter {
  return value === 'all' || value === 'error' || value === 'warning' || value === 'info';
}

const toLogLevel = (value: unknown): LogEntry['level'] => {
  if (value === 'warning' || value === 'error' || value === 'debug') {
    return value;
  }
  return 'info';
};

const toLogService = (service: unknown, source: unknown): string => {
  if (typeof service === 'string') return service;
  if (typeof source === 'string') return source;
  return 'raptor';
};

const toLogMessage = (message: unknown, msg: unknown, fallback: string): string => {
  if (typeof message === 'string') return message;
  if (typeof msg === 'string') return msg;
  return fallback;
};

const parseLogLine = (line: string, index: number): LogEntry => {
  try {
    const parsed = JSON.parse(line) as Record<string, unknown>;

    return {
      id: typeof parsed.id === 'string' ? parsed.id : `log-${index}`,
      timestamp:
        typeof parsed.timestamp === 'string' ? parsed.timestamp : new Date().toISOString(),
      level: toLogLevel(parsed.level),
      service: toLogService(parsed.service, parsed.source),
      message: toLogMessage(parsed.message, parsed.msg, line),
      details: parsed.details ?? parsed.metadata ?? parsed.context,
    };
  } catch {
    return {
      id: `log-${index}`,
      timestamp: new Date().toISOString(),
      level: 'info',
      service: 'raptor',
      message: line,
    };
  }
};

const parseRaptorLogs = (payload: RaptorLogsPayload): LogEntry[] => {
  const raw = payload?.log_tail ?? '';
  const lines = raw
    .split('\n')
    .map((line: string) => line.trim())
    .filter(Boolean);

  return lines.map(parseLogLine);
};

interface LogsSidebarProps {
  filter: LogFilter;
  onFilterChange: (filter: LogFilter) => void;
  serviceFilter: string;
  onServiceFilterChange: (service: string) => void;
  services: string[];
  autoRefresh: boolean;
  onAutoRefreshChange: (value: boolean) => void;
  isRefreshing: boolean;
  onRefresh: () => void;
  onClearDisplay: () => void;
  logs: LogEntry[];
}

const LogsSidebar = ({
  filter,
  onFilterChange,
  serviceFilter,
  onServiceFilterChange,
  services,
  autoRefresh,
  onAutoRefreshChange,
  isRefreshing,
  onRefresh,
  onClearDisplay,
  logs,
}: LogsSidebarProps) => (
  <div className="space-y-4">
    <div>
      <h2 className="text-lg font-semibold text-text mb-3">Logs & Events</h2>
      <p className="text-xs text-muted mb-4">Backend errors, failed requests, and system events</p>
    </div>

    <div>
      <label className="block text-xs font-medium text-text mb-2">Level Filter</label>
      <select
        value={filter}
        onChange={e => {
          const nextFilter = e.target.value;
          if (isLogFilter(nextFilter)) {
            onFilterChange(nextFilter);
          }
        }}
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
        onChange={e => onServiceFilterChange(e.target.value)}
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

    <div className="flex items-center gap-2">
      <input
        type="checkbox"
        id="auto-refresh"
        checked={autoRefresh}
        onChange={e => onAutoRefreshChange(e.target.checked)}
        className="rounded border-border text-primary focus:ring-primary"
      />
      <label htmlFor="auto-refresh" className="text-xs text-text">
        Auto-refresh (5s)
      </label>
    </div>

    <div className="space-y-2">
      <Button
        variant="primary"
        size="sm"
        fullWidth
        icon="🔄"
        onClick={onRefresh}
        disabled={isRefreshing}
        loading={isRefreshing}
        aria-label="Refresh logs"
      >
        Refresh Logs
      </Button>
      <Button
        variant="danger"
        size="sm"
        fullWidth
        icon="🗑️"
        onClick={onClearDisplay}
        aria-label="Clear logs display"
      >
        Clear Display
      </Button>
    </div>

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

interface LogEntriesProps {
  logs: LogEntry[];
  selectedLog: LogEntry | null;
  onSelectLog: (log: LogEntry | null) => void;
  filter: LogFilter;
  serviceFilter: string;
}

const LogEntries = ({ logs, selectedLog, onSelectLog, filter, serviceFilter }: LogEntriesProps) => {
  if (logs.length === 0) {
    return (
      <div className="bg-surface rounded-xl shadow-sm border border-border p-12 text-center">
        <div className="text-6xl mb-4" aria-hidden="true">📋</div>
        <h3 className="text-lg font-medium text-text mb-2">No Logs Found</h3>
        <p className="text-muted">
          {filter !== 'all' || serviceFilter !== 'all'
            ? 'Try adjusting your filters'
            : 'System logs will appear here'}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {logs.map(log => {
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
              onClick={() => onSelectLog(isSelected ? null : log)}
              className="w-full text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary rounded"
              aria-controls={detailsId}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${colors.bg} ${colors.text}`}>
                    <span className={`inline-block w-2 h-2 rounded-full ${colors.dot} mr-2`} aria-hidden="true"></span>
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
      })}
    </div>
  );
};

/**
 * Debug/Event Log: Recent backend errors, failed requests, and system events
 */
const LogsPageContent = () => {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState<LogFilter>('all');
  const [serviceFilter, setServiceFilter] = useState<string>('all');
  const [selectedLog, setSelectedLog] = useState<LogEntry | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [dismissedError, setDismissedError] = useState(false);

  const { data: logs = [], isLoading, isFetching, error, refetch } = useQuery<LogEntry[]>({
    queryKey: queryKeys.raptorLogs(100),
    queryFn: async () => {
      const logsData = (await apiClient.getRaptorLogs(100)) as RaptorLogsPayload;
      return parseRaptorLogs(logsData);
    },
    refetchInterval: autoRefresh ? 5000 : false,
    staleTime: 2000,
  });

  useEffect(() => {
    if (error) setDismissedError(false);
  }, [error]);

  const filteredLogs = useMemo(
    () =>
      logs.filter(log => {
        if (filter !== 'all' && log.level !== filter) return false;
        if (serviceFilter !== 'all' && log.service !== serviceFilter) return false;
        return true;
      }),
    [logs, filter, serviceFilter],
  );

  const services = ['all', ...Array.from(new Set(logs.map(log => log.service)))];

  const sidebar = (
    <LogsSidebar
      filter={filter}
      onFilterChange={setFilter}
      serviceFilter={serviceFilter}
      onServiceFilterChange={setServiceFilter}
      services={services}
      autoRefresh={autoRefresh}
      onAutoRefreshChange={setAutoRefresh}
      isRefreshing={isFetching}
      onRefresh={() => {
        void refetch();
      }}
      onClearDisplay={() => {
        queryClient.setQueryData<LogEntry[]>(queryKeys.raptorLogs(100), []);
      }}
      logs={logs}
    />
  );

  const showError = Boolean(error) && !dismissedError;

  const mainContent = (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-text mb-2">System Logs</h1>
        <p className="text-muted">Real-time monitoring of backend errors, warnings, and system events</p>
      </div>

      {showError && (
        <Alert
          variant="danger"
          title="Failed to Load Logs"
          message={
            <>
              <p className="mb-3">{error instanceof Error ? error.message : 'Failed to load logs'}</p>
              <Button
                variant="danger"
                size="sm"
                icon="🔄"
                onClick={() => {
                  setDismissedError(false);
                  void refetch();
                }}
                aria-label="Retry loading logs"
              >
                Retry
              </Button>
            </>
          }
          dismissible
          onDismiss={() => setDismissedError(true)}
        />
      )}

      {isLoading && <ListSkeleton count={8} />}

      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {!isLoading && logs.length > 0 && `Logs updated. Showing ${filteredLogs.length} of ${logs.length} entries`}
      </div>

      {!isLoading && (
        <LogEntries
          logs={filteredLogs}
          selectedLog={selectedLog}
          onSelectLog={setSelectedLog}
          filter={filter}
          serviceFilter={serviceFilter}
        />
      )}
    </div>
  );

  return <TwoColumnLayout sidebar={sidebar}>{mainContent}</TwoColumnLayout>;
};

export default LogsPageContent;
