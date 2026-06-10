export default function ChatLoading() {
  return (
    <div
      className="flex flex-col h-full min-h-[60vh] bg-bg"
      role="status"
      aria-label="Loading chat"
    >
      {/* Message list area */}
      <div className="flex-1 overflow-hidden p-4 space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className={`flex gap-3 ${i % 2 === 0 ? 'flex-row-reverse' : ''}`}>
            <div className="w-8 h-8 rounded-full bg-surface-hover animate-pulse flex-none" />
            <div className="space-y-2 flex-1 max-w-[70%]">
              <div className="h-4 bg-surface-hover rounded animate-pulse w-3/4" />
              <div className="h-4 bg-surface-hover rounded animate-pulse w-1/2" />
            </div>
          </div>
        ))}
      </div>
      {/* Input area */}
      <div className="border-t border-border p-4">
        <div className="h-12 bg-surface-hover rounded-xl animate-pulse" />
      </div>
      <span className="sr-only">Loading conversation...</span>
    </div>
  );
}
