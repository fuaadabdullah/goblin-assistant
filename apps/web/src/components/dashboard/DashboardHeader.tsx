import Button from '../ui/Button';

interface Props {
  onRefresh: () => void;
  autoRefresh: boolean;
  onToggleAutoRefresh: () => void;
  loading: boolean;
}

export const DashboardHeader = ({ onRefresh, autoRefresh, onToggleAutoRefresh, loading }: Props) => {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div>
        <h1 className="text-2xl font-semibold text-text">Welcome</h1>
        <p className="text-sm text-muted">
          Start a chat, find answers, or check system status at a glance.
        </p>
      </div>
      <div className="flex items-center gap-3">
        <Button variant="secondary" onClick={onRefresh} disabled={loading}>
          {loading ? 'Refreshing...' : 'Refresh'}
        </Button>
        <Button variant={autoRefresh ? 'success' : 'ghost'} onClick={onToggleAutoRefresh}>
          {autoRefresh ? 'Auto-refresh on' : 'Auto-refresh off'}
        </Button>
      </div>
    </div>
  );
};
