export default function LogsLoading() {
  return (
    <div className="p-6 space-y-4" role="status" aria-label="Loading logs">
      <div className="h-8 w-32 bg-surface-hover rounded animate-pulse mb-6" />
      {[1, 2, 3, 4, 5, 6].map((i) => (
        <div
          key={i}
          className="bg-surface rounded-lg border border-border p-4 animate-pulse space-y-2"
        >
          <div className="flex items-center gap-3">
            <div className="h-5 w-16 bg-surface-hover rounded-full" />
            <div className="h-4 w-24 bg-surface-hover rounded" />
          </div>
          <div className="h-4 w-full bg-surface-hover rounded" />
          <div className="h-4 w-2/3 bg-surface-hover rounded" />
        </div>
      ))}
      <span className="sr-only">Loading logs...</span>
    </div>
  );
}
