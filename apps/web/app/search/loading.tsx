export default function SearchLoading() {
  return (
    <div className="p-6" role="status" aria-label="Loading search">
      {/* Search bar skeleton */}
      <div className="h-12 bg-surface-hover rounded-xl animate-pulse mb-6 max-w-2xl" />
      {/* Results skeleton */}
      <div className="space-y-4 max-w-2xl">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="bg-surface rounded-xl border border-border p-4 animate-pulse space-y-2"
          >
            <div className="h-5 w-3/4 bg-surface-hover rounded" />
            <div className="h-4 w-full bg-surface-hover rounded" />
            <div className="h-4 w-1/2 bg-surface-hover rounded" />
          </div>
        ))}
      </div>
      <span className="sr-only">Loading search results...</span>
    </div>
  );
}
