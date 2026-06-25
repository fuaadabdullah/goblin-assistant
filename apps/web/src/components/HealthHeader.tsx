import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { queryKeys } from '../lib/query-keys';
import type { HealthStatus } from '../types/api';

interface HealthData {
  status: 'healthy' | 'degraded' | 'down';
  latency_ms?: number | undefined;
  last_check?: string | undefined;
  services?: Record<string, string> | undefined;
}

const mapOverallStatus = (overall: string | undefined): HealthData['status'] => {
  if (overall === 'healthy' || overall === 'ok') return 'healthy';
  if (overall === 'degraded' || overall === 'warnings' || overall === 'warning') return 'degraded';
  return 'down';
};

const getOverallHealth = (data: HealthStatus): string | undefined => {
  const record = data as unknown as Record<string, unknown>;
  return typeof record['overall'] === 'string'
    ? record['overall']
    : typeof record['status'] === 'string'
      ? record['status']
      : undefined;
};

const getHealthServices = (data: HealthStatus): Record<string, { status?: string }> => {
  const record = data as unknown as Record<string, unknown>;
  const services = record['services'];
  if (services && typeof services === 'object') {
    return services as Record<string, { status?: string }>;
  }
  const components = record['components'];
  if (components && typeof components === 'object') {
    return components as Record<string, { status?: string }>;
  }
  return {};
};

interface HealthHeaderProps {
  className?: string;
  /** Compact mode hides heartbeat & latency, shows only pill */
  compact?: boolean;
}

const createHealthData = async (): Promise<HealthData> => {
  const startTime = Date.now();

  try {
    const data = await apiClient.getAllHealth();
    const latency = Date.now() - startTime;

    const services = getHealthServices(data);
    const serviceStatuses = Object.values(services).map((service) => service?.status);
    let status: HealthData['status'] = mapOverallStatus(getOverallHealth(data));

    if (serviceStatuses.some((s) => s === 'unhealthy' || s === 'down' || s === 'error')) {
      status = 'down';
    } else if (serviceStatuses.some((s) => s === 'degraded' || s === 'unknown')) {
      status = 'degraded';
    }

    return {
      status,
      latency_ms: latency,
      last_check: new Date().toISOString(),
      services: Object.entries(services).reduce<NonNullable<HealthData['services']>>(
        (acc, [key, value]) => {
          if (typeof value?.status === 'string') {
            acc[key as keyof HealthData['services']] = value.status;
          }
          return acc;
        },
        {}
      ),
    };
  } catch {
    return {
      status: 'down',
      latency_ms: undefined,
      last_check: new Date().toISOString(),
    };
  }
};

/**
 * Global health status indicator in header
 * Shows aggregated system health with latency and last heartbeat
 */
const HealthHeader = ({ className = '', compact = false }: HealthHeaderProps) => {
  const { data: health, isLoading: loading } = useQuery({
    queryKey: queryKeys.health,
    queryFn: createHealthData,
    refetchInterval: 10_000,
    staleTime: 5_000,
  });

  if (loading) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="animate-pulse h-6 w-24 bg-surface-hover rounded-full"></div>
      </div>
    );
  }

  if (!health) return null;

  const statusConfig = {
    healthy: {
      bg: 'bg-success/20',
      text: 'text-success',
      dot: 'bg-success',
      label: 'OK',
      icon: '✓',
    },
    degraded: {
      bg: 'bg-warning/20',
      text: 'text-warning',
      dot: 'bg-warning',
      label: 'Degraded',
      icon: '⚠',
    },
    down: {
      bg: 'bg-danger/20',
      text: 'text-danger',
      dot: 'bg-danger',
      label: 'Down',
      icon: '✗',
    },
  };

  const config = statusConfig[health.status];
  const lastCheckTime = health.last_check
    ? new Date(health.last_check).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : 'Unknown';

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Status Pill */}
      <div
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full ${config.bg} ${config.text} text-xs font-medium`}
        title={`Last checked: ${lastCheckTime}`}
      >
        <span className={`w-2 h-2 rounded-full ${config.dot} animate-pulse`}></span>
        <span className="font-mono">{config.icon}</span>
        <span>{config.label}</span>
      </div>

      {/* Latency */}
      {!compact && health.latency_ms !== undefined && (
        <div className="flex items-center gap-1 text-xs text-muted">
          <span className="font-mono">{health.latency_ms}ms</span>
        </div>
      )}

      {/* Last Heartbeat */}
      {!compact && (
        <div className="hidden sm:flex items-center gap-1 text-xs text-muted">
          <span>💓</span>
          <span className="font-mono">{lastCheckTime}</span>
        </div>
      )}
    </div>
  );
};

export default HealthHeader;
