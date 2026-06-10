export default function SandboxLoading() {
  return (
    <div
      className="flex flex-col h-full min-h-[70vh] p-4 gap-4"
      role="status"
      aria-label="Loading sandbox"
    >
      {/* Toolbar */}
      <div className="flex gap-2">
        <div className="h-9 w-28 bg-surface-hover rounded-lg animate-pulse" />
        <div className="h-9 w-20 bg-surface-hover rounded-lg animate-pulse" />
        <div className="ml-auto h-9 w-24 bg-surface-hover rounded-lg animate-pulse" />
      </div>
      {/* Editor + output split */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1">
        <div className="bg-surface rounded-xl border border-border animate-pulse min-h-[300px]" />
        <div className="bg-surface rounded-xl border border-border animate-pulse min-h-[300px]" />
      </div>
      <span className="sr-only">Loading sandbox...</span>
    </div>
  );
}
