import Alert from '../ui/Alert';
import Button from '../ui/Button';

interface Props {
  error: string;
  onRetry: () => void;
}

export const DashboardError = ({ error, onRetry }: Props) => {
  return (
    <div className="flex items-center justify-between gap-4 bg-surface border border-border rounded-lg p-4">
      <Alert variant="warning" title="Dashboard warning" message={error} />
      <Button variant="secondary" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
};
