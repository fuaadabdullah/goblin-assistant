export default function SettingsLoading() {
  return (
    <div className="p-6 max-w-3xl" role="status" aria-label="Loading settings">
      <div className="h-8 w-36 bg-surface-hover rounded animate-pulse mb-6" />
      {[1, 2, 3].map((i) => (
        <div key={i} className="bg-surface rounded-xl border border-border p-6 mb-4 animate-pulse">
          <div className="h-5 w-40 bg-surface-hover rounded mb-4" />
          <div className="space-y-3">
            <div className="h-10 bg-surface-hover rounded-lg" />
            <div className="h-10 bg-surface-hover rounded-lg" />
          </div>
        </div>
      ))}
      <span className="sr-only">Loading settings...</span>
    </div>
  );
}
