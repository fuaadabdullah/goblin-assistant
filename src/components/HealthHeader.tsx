import { useEffect, useState } from 'react';
import { apiClient } from '../api/apiClient';

interface HealthData {
  status: 'healthy' | 'degraded' | 'down';
  latency_ms?: number;
  last_check?: string;
  services?: {
    routing?: string;
    execution?: string;
    search?: string;
    auth?: string;
  };
}

interface HealthHeaderProps {
  className?: string;
  /** Compact mode hides heartbeat & latency, shows only pill */
  compact?: boolean;
}

/**
 * Global health status indicator in header
 * Shows aggregated system health with latency and last heartbeat
 */
const HealthHeader = ({ className = '', compact = false }: HealthHeaderProps) => {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkHealth = async () => {
      const startTime = Date.now();
      try {
        const data = (await apiClient.getAllHealth()) as HealthData; // Cast to expected shape
        const latency = Date.now() - startTime;

        // Aggregate health status from services
        const services = (data.services || {}) as Record<string, string | undefined>;
        const serviceStatuses = Object.values(services);
        let status: 'healthy' | 'degraded' | 'down' = 'healthy';

        if (serviceStatuses.some((s: any) => s === 'down' || s === 'error')) {
          status = 'down';
        } else if (serviceStatuses.some((s: any) => s === 'degraded' || s === 'warning')) {
          status = 'degraded';
        }

        setHealth({
          status,
          latency_ms: latency,
          last_check: new Date().toISOString(),
          services: data.services,
        });
      } catch (error) {
        setHealth({
          status: 'down',
          latency_ms: undefined,
          last_check: new Date().toISOString(),
        });
      } finally {
        setLoading(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 10000); // Check every 10s

    return () => clearInterval(interval);
  }, []);

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
