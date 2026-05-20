import type { TestResult } from '../hooks/useProviderMutations';

export default function ProviderTestResultBanner({
  result,
  onDismiss,
}: {
  result: TestResult;
  onDismiss: () => void;
}) {
  return (
    <div
      className={`p-4 rounded-lg border ${
        result.success ? 'bg-success/20 border-success' : 'bg-danger/20 border-danger'
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="text-xl" aria-hidden="true">
          {result.success ? '✓' : '✗'}
        </span>
        <div className="flex-1">
          <h3
            className={`text-sm font-semibold mb-1 ${
              result.success ? 'text-success' : 'text-danger'
            }`}
          >
            {result.success ? 'Test Successful' : 'Test Failed'}
          </h3>
          <p className={`text-sm ${result.success ? 'text-success' : 'text-danger'}`}>
            {result.message}
          </p>
          <div className="flex items-center gap-4 mt-2 text-xs text-muted">
            <span>Latency: {result.latency}ms</span>
            {result.model_used && <span>Model: {result.model_used}</span>}
          </div>
          {result.response && (
            <div className="mt-3 p-3 bg-bg rounded border border-border">
              <h4 className="text-xs font-semibold text-text mb-2">Sample Response:</h4>
              <pre className="text-xs text-text whitespace-pre-wrap">{result.response}</pre>
            </div>
          )}
        </div>
        <button
          onClick={onDismiss}
          className={
            result.success ? 'text-success hover:text-success/80' : 'text-danger hover:text-danger/80'
          }
          aria-label="Dismiss"
          type="button"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

