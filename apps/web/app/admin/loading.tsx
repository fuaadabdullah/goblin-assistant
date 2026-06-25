export default function AdminLoading() {
  return (
    <div className="min-h-screen bg-bg p-8" role="status" aria-label="Loading dashboard">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="h-8 w-40 bg-surface-hover rounded animate-pulse" />
        <div className="h-9 w-32 bg-surface-hover rounded-lg animate-pulse" />
      </div>
      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-16 bg-surface rounded-xl border border-border animate-pulse" />
        ))}
      </div>
      {/* Chart grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {[1, 2].map((i) => (
          <div key={i} className="h-64 bg-surface rounded-xl border border-border animate-pulse" />
        ))}
      </div>
      {/* Activity list */}
      <div className="bg-surface rounded-xl border border-border p-6 animate-pulse">
        <div className="h-6 w-36 bg-surface-hover rounded mb-4" />
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-14 bg-surface-hover rounded-md" />
          ))}
        </div>
      </div>
      <span className="sr-only">Loading admin dashboard...</span>
    </div>
  );
}
