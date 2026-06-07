export default function ProvidersLoading() {
  return (
    <div className="p-6 space-y-4" role="status" aria-label="Loading providers">
      <div className="h-8 w-36 bg-surface-hover rounded animate-pulse mb-6" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div
            key={i}
            className="bg-surface rounded-lg border border-border p-4 animate-pulse"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-surface-hover rounded" />
              <div>
                <div className="h-5 w-28 bg-surface-hover rounded mb-1" />
                <div className="h-3 w-18 bg-surface-hover rounded" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="h-4 bg-surface-hover rounded" />
              <div className="h-4 bg-surface-hover rounded" />
            </div>
          </div>
        ))}
      </div>
      <span className="sr-only">Loading providers...</span>
    </div>
  );
}
