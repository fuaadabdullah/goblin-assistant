'use client';

import { useEffect } from 'react';

export default function RetrievalDebugError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('debug-retrieval-error', error);
  }, [error]);

  return (
    <div className="min-h-[40vh] flex flex-col items-center justify-center gap-4 p-8 text-center">
      <h2 className="text-2xl font-semibold text-text">Retrieval debugger failed</h2>
      <p className="max-w-xl text-sm text-muted">
        The retrieval diagnostics could not be loaded. Check API connectivity and ops access, then
        retry.
      </p>
      <button
        type="button"
        onClick={reset}
        className="rounded-lg border border-border bg-surface px-4 py-2 text-sm text-text hover:bg-surface-hover"
      >
        Try again
      </button>
    </div>
  );
}
