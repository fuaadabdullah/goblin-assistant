import Link from 'next/link';
import { Menu, X } from 'lucide-react';

interface ChatHeaderProps {
  /** Show admin-only shortcuts when true. */
  isAdmin: boolean;
  /** Handler for clearing the current chat. */
  onClear: () => void;
  /** Toggle mobile conversation drawer. */
  onToggleSidebar?: () => void;
  /** Whether mobile conversation drawer is open. */
  isSidebarOpen?: boolean;
  /** Show mobile sidebar toggle button. */
  showSidebarToggle?: boolean;
}

const ChatHeader = ({
  isAdmin,
  onClear,
  onToggleSidebar,
  isSidebarOpen = false,
  showSidebarToggle = false,
}: ChatHeaderProps) => (
  <header className="sticky top-0 z-20 border-b border-border/70 bg-surface/85 backdrop-blur px-6 py-4">
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
      <div className="space-y-2 flex-1">
        <div className="flex items-start justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-2xl font-semibold text-text">AI Orchestration Console</h1>
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-hover px-3 py-1 text-xs text-muted">
              <span className="h-2 w-2 rounded-full bg-success" />
              Live gateway
            </span>
          </div>
          {showSidebarToggle && onToggleSidebar ? (
            <button
              type="button"
              onClick={onToggleSidebar}
              className="lg:hidden inline-flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text hover:bg-surface-hover"
              aria-label={isSidebarOpen ? 'Close conversations' : 'Open conversations'}
              aria-expanded={isSidebarOpen}
              aria-controls="mobile-chat-sidebar"
            >
              {isSidebarOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
              <span>Conversations</span>
            </button>
          ) : null}
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
