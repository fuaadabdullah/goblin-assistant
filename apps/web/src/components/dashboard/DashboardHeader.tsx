'use client';

import { RefreshCw } from 'lucide-react';

interface DashboardHeaderProps {
  autoRefresh: boolean;
  loading?: boolean;
  refreshing?: boolean;
  onToggleAutoRefresh: () => void;
  onRefresh: () => void;
  title?: string;
  description?: string;
}

export const DashboardHeader = ({
  autoRefresh,
  loading,
  refreshing,
  onToggleAutoRefresh,
  onRefresh,
  title = 'Welcome',
  description = 'Start a chat to see live operations metrics and provider health.',
}: DashboardHeaderProps) => {
  const isLoading = loading ?? refreshing ?? false;

  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <h1 className="text-xl font-semibold text-text">{title}</h1>
        <p className="text-sm text-muted">{description}</p>
      </div>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleAutoRefresh}
          className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
            autoRefresh
              ? 'bg-primary/10 border-primary/40 text-primary'
              : 'border-border text-muted hover:border-border/80 hover:text-text'
          }`}
          >
          {autoRefresh ? 'Auto-refresh on' : 'Auto-refresh off'}
        </button>
        <button
          type="button"
          onClick={onRefresh}
          disabled={isLoading}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-border text-muted hover:text-text hover:border-border/80 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
          {isLoading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
    </div>
  );
};

export default DashboardHeader;
