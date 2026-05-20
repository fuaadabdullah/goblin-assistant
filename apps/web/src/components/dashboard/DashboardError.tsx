import { InlineErrorState } from '../ui';

interface Props {
  error: string;
  onRetry: () => void;
}

export const DashboardError = ({ error, onRetry }: Props) => {
  return (
    <InlineErrorState
      title="Dashboard warning"
      message={error}
      retryLabel="Retry"
      onRetry={onRetry}
      className="w-full"
    />
  );
};
