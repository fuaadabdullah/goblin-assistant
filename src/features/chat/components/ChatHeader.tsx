import Link from 'next/link';

interface ChatHeaderProps {
  /** Show admin-only shortcuts when true. */
  isAdmin: boolean;
  /** Handler for clearing the current chat. */
  onClear: () => void;
}

const ChatHeader = ({ isAdmin, onClear }: ChatHeaderProps) => (
  <header className="sticky top-0 z-20 border-b border-border/70 bg-surface/85 backdrop-blur px-6 py-4">
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold text-text">AI Orchestration Console</h1>
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-hover px-3 py-1 text-xs text-muted">
            <span className="h-2 w-2 rounded-full bg-success" />
            Live gateway
          </span>
        </div>
        <p className="text-sm text-muted">
          Route requests, optimize costs, monitor reliability. Control the LLM ecosystem end-to-end.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={onClear}
          className="px-3 py-2 rounded-lg border border-border text-text hover:bg-surface-hover"
          type="button"
        >
          Clear Chat
        </button>
        <Link
          href="/search"
          className="px-3 py-2 rounded-lg bg-primary/15 text-primary hover:bg-primary/25"
        >
          Global Search
        </Link>
        {isAdmin && (
          <Link
            href="/admin"
            className="px-3 py-2 rounded-lg bg-surface-hover text-text hover:bg-surface-active"
          >
            Admin Dashboard
          </Link>
        )}
      </div>
    </div>
  </header>
);

export default ChatHeader;
