export default function AgentLoading() {
  return (
    <div className="flex min-h-[70vh] flex-col gap-4 p-6" role="status" aria-label="Loading agent loop">
      <div className="h-10 w-72 animate-pulse rounded-lg bg-surface-hover" />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="min-h-[520px] animate-pulse rounded-2xl border border-border bg-surface" />
        <div className="min-h-[520px] animate-pulse rounded-2xl border border-border bg-surface" />
      </div>
      <span className="sr-only">Loading agent loop...</span>
    </div>
  );
}

