import { useState } from 'react';
import Sparkline from './Sparkline';
import { Button } from './ui';

interface HealthCardProps {
  title: string;
  status: 'healthy' | 'degraded' | 'down' | 'unknown';
  icon: string;
  metrics?: { label: string; value: string | number }[];
  lastCheck?: string;
  latencyData?: number[];
  errors?: { timestamp: string; message: string }[];
  onRetest?: () => Promise<void>;
  expandable?: boolean;
}

const statusConfig = {
  healthy: {
    bg: 'bg-surface',
    border: 'border-success',
    text: 'text-success',
    badge: 'bg-success/20 text-success',
    icon: '✓',
  },
  degraded: {
    bg: 'bg-surface',
    border: 'border-warning',
    text: 'text-warning',
    badge: 'bg-warning/20 text-warning',
    icon: '⚠',
  },
  down: {
    bg: 'bg-surface',
    border: 'border-danger',
    text: 'text-danger',
    badge: 'bg-danger/20 text-danger',
    icon: '✗',
  },
  unknown: {
    bg: 'bg-surface',
    border: 'border-border',
    text: 'text-muted',
    badge: 'bg-surface-hover text-muted',
    icon: '?',
  },
};

/**
 * HealthCard - Expandable status card for monitoring services
 * Shows status, metrics, sparkline, and recent errors
 */
export default function HealthCard({
  title,
  status,
  icon,
  metrics = [],
  lastCheck,
  latencyData = [],
  errors = [],
  onRetest,
  expandable = true,
}: HealthCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const config = statusConfig[status];

  const handleRetest = async () => {
    if (!onRetest) return;
    setIsTesting(true);
    try {
      await onRetest();
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div
      className={`rounded-xl border-2 transition-all ${config.border} ${
        isExpanded ? config.bg : 'bg-surface'
      } min-h-[220px]`}
    >
      {/* Card Header */}
      <button
        onClick={() => expandable && setIsExpanded(!isExpanded)}
        className={`w-full p-6 flex items-center justify-between ${
          expandable ? 'cursor-pointer hover:bg-surface-hover' : 'cursor-default'
        }`}
        disabled={!expandable}
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center justify-center w-8 h-8 text-2xl">{icon}</div>
          <div className="text-left">
            <h3 className="text-sm font-semibold text-text">{title}</h3>
            <span className={`text-xs px-2 py-0.5 rounded-full ${config.badge}`}>
              {config.icon} {status.charAt(0).toUpperCase() + status.slice(1)}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Sparkline */}
          {latencyData.length > 0 && (
            <div className="hidden sm:block">
              <Sparkline
                data={latencyData}
                width={80}
                height={24}
                color={status === 'healthy' ? 'var(--success)' : 'var(--primary)'}
                showFill
              />
            </div>
          )}

          {expandable && (
            <svg
              className={`w-5 h-5 text-muted transition-transform ${
                isExpanded ? 'rotate-180' : ''
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-6 pb-6 space-y-6 border-t border-border">
          {/* Metrics Grid */}
          {metrics.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-4">
              {metrics.map((metric, idx) => (
                <div
                  key={idx}
                  className="bg-surface-hover rounded-lg p-4 border border-border min-h-[72px]"
                >
                  <div className="text-xs text-muted mb-1">{metric.label}</div>
                  <div className="text-lg font-semibold text-text leading-tight">
                    {metric.value}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Last Check */}
          {lastCheck && (
            <div className="text-xs text-muted">
              Last checked: {new Date(lastCheck).toLocaleString()}
            </div>
          )}

          {/* Recent Errors */}
          {errors.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-text mb-2">
                Recent Errors ({errors.length})
              </h4>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {errors.map((error, idx) => (
                  <div key={idx} className="bg-surface border border-danger rounded p-2">
                    <div className="text-xs text-danger font-mono">{error.message}</div>
                    <div className="text-xs text-muted mt-1">
                      {new Date(error.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Retest Button */}
          {onRetest && (
            <Button
              onClick={handleRetest}
              disabled={isTesting}
              loading={isTesting}
              variant="primary"
              fullWidth
              icon={!isTesting && <span>🧪</span>}
            >
              {isTesting ? 'Testing...' : 'Re-run Test'}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
