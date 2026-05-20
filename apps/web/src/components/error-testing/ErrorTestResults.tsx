import type { ErrorTestResult } from '../../hooks/useErrorTesting';

interface Props {
  results: ErrorTestResult[];
}

export const ErrorTestResults = ({ results }: Props) => {
  if (results.length === 0) {
    return <div className="text-sm text-muted">No test results yet.</div>;
  }

  return (
    <div className="bg-bg border border-border rounded-lg p-4">
      <h4 className="text-sm font-semibold mb-3">Test Results</h4>
      <ul className="space-y-2 text-sm">
        {results.map(result => (
          <li key={result.id} className="flex items-start justify-between gap-3">
            <div>
              <div className="font-medium">{result.label}</div>
              <div className="text-xs text-muted">{new Date(result.timestamp).toLocaleString()}</div>
              {result.message && <div className="text-xs text-muted">{result.message}</div>}
            </div>
            <span
              className={`px-2 py-1 text-xs rounded-full ${
                result.status === 'success' ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'
              }`}
            >
              {result.status}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
};
