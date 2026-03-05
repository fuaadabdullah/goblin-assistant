import type { ReactNode } from 'react';
import Card from './Card';
import Badge from './ui/Badge';
import Tooltip from './ui/Tooltip';

type StatusKind = 'healthy' | 'degraded' | 'down' | 'unknown';

export interface StatusCardProps {
  title: string;
  status: StatusKind;
  icon?: ReactNode;
  meta?: Array<{ label: string; value: string | number }>;
  lastCheck?: string;
  statusDetails?: string;
  className?: string;
}

const statusConfig: Record<
  StatusKind,
  {
    border: string;
    badgeVariant: 'success' | 'warning' | 'danger' | 'neutral';
    icon: string;
    description: string;
    ariaLabel: string;
  }
> = {
  healthy: {
    border: 'border-success',
    badgeVariant: 'success',
    icon: '✓',
    description: 'Service is operational and responding normally',
    ariaLabel: 'Status: Healthy - Service is fully operational',
  },
  degraded: {
    border: 'border-warning',
    badgeVariant: 'warning',
    icon: '⚠',
    description:
      'Service is experiencing issues but remains partially functional. Some features may be unavailable or slow.',
    ariaLabel: 'Status: Degraded - Service has reduced functionality',
  },
  down: {
    border: 'border-danger',
    badgeVariant: 'danger',
    icon: '✗',
    description: 'Service is completely unavailable and not responding to requests',
    ariaLabel: 'Status: Down - Service is not available',
  },
  unknown: {
    border: 'border-border',
    badgeVariant: 'neutral',
    icon: '?',
    description:
      'Unable to determine service status. Check may have timed out or service is unreachable.',
    ariaLabel: 'Status: Unknown - Cannot determine service status',
  },
};

/**
 * StatusCard — lightweight, reusable status widget.
 * Shows a title, status chip (color-coded with tooltip), optional icon,
 * last updated timestamp, and a small meta list.
 */
export default function StatusCard({
  title,
  status,
  icon,
  meta = [],
  lastCheck,
  statusDetails,
  className = '',
}: StatusCardProps) {
  const config = statusConfig[status];

  // Format timestamp for display
  const formatLastCheck = (timestamp?: string) => {
    if (!timestamp) return null;
    try {
      const date = new Date(timestamp);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffSecs = Math.floor(diffMs / 1000);
      const diffMins = Math.floor(diffSecs / 60);
      const diffHours = Math.floor(diffMins / 60);

      if (diffSecs < 60) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      return date.toLocaleDateString();
    } catch {
      return null;
    }
  };

  const timeAgo = formatLastCheck(lastCheck);
  const tooltipContent = statusDetails || config.description;

  return (
    <Card
      className={`border-2 ${config.border} ${className}`}
      role="group"
      aria-label={`${title} ${config.ariaLabel}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {icon && (
            <div className="flex items-center justify-center w-8 h-8 text-2xl flex-shrink-0">
              {icon}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-text leading-none mb-2">{title}</h3>
            <Tooltip content={tooltipContent} position="bottom">
              <div className="inline-block">
                <Badge
                  variant={config.badgeVariant}
                  icon={config.icon}
                  aria-label={config.ariaLabel}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </Badge>
              </div>
            </Tooltip>
          </div>
        </div>
        {timeAgo && (
          <div className="text-xs text-muted flex-shrink-0" title={lastCheck}>
            {timeAgo}
          </div>
        )}
      </div>

      {meta.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-4">
          {meta.map((m, i) => (
            <div
              key={i}
              className="bg-surface-hover rounded-lg p-3 border border-border min-h-[64px]"
            >
              <div className="text-xs text-muted mb-1">{m.label}</div>
              <div className="text-sm font-semibold text-text leading-tight">{m.value}</div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
