import Link from 'next/link';
import type { ChatThread } from '../types';

interface ChatSidebarProps {
  /** Conversation threads list. */
  threads: ChatThread[];
  /** Whether threads are loading. */
  isThreadsLoading: boolean;
  /** Active thread key. */
  activeThreadKey: string | null;
  /** Select a thread from the list. */
  onSelectThread: (threadKey: string) => void;
  /** Handler for starting a new conversation. */
  onNewConversation: () => void;
  /** Whether admin-only stats should display. */
  isAdmin: boolean;
  /** Total tokens used in the current chat. */
  totalTokens: number;
  /** Message count in the current chat. */
  messageCount: number;
  /** Optional additional classes for layout context (desktop/mobile drawer). */
  className?: string;
}

const ChatSidebar = ({
  threads,
  isThreadsLoading,
  activeThreadKey,
  onSelectThread,
  onNewConversation,
  isAdmin,
  totalTokens,
  messageCount,
  className = '',
}: ChatSidebarProps) => (
  <aside className={`flex w-72 border-r border-border bg-surface px-4 py-6 flex-col gap-6 ${className}`}>
    <div>
      <h2 className="text-sm font-semibold text-text mb-2">Conversations</h2>
      <button
        onClick={onNewConversation}
        className="w-full px-3 py-2 rounded-lg text-sm font-medium bg-primary/15 text-primary hover:bg-primary/25"
        type="button"
      >
        New Conversation
      </button>
    </div>

    <div className="space-y-2 overflow-y-auto pr-1">
      {isThreadsLoading ? (
        <div className="rounded-xl border border-border bg-bg px-3 py-3 space-y-3 animate-pulse">
          <div className="h-3 w-20 bg-surface-hover rounded" />
          <div className="h-4 w-full bg-surface-hover rounded" />
          <div className="h-3 w-3/4 bg-surface-hover rounded" />
        </div>
      ) : threads.length > 0 ? (
        <ul className="space-y-2">
          {threads.map(thread => {
            const isActive = thread.threadKey === activeThreadKey;
            return (
              <li key={thread.threadKey}>
                <button
                  type="button"
                  onClick={() => onSelectThread(thread.threadKey)}
                  aria-current={isActive ? 'true' : undefined}
                  className={`w-full text-left rounded-xl border px-3 py-3 hover:bg-surface-hover ${
                    isActive ? 'border-primary/40 bg-primary/10' : 'border-border bg-bg'
                  }`}
                >
                  <div className="text-sm text-text font-medium line-clamp-1">
                    {thread.title || 'Untitled chat'}
                  </div>
                  <div className="text-xs text-muted line-clamp-2 mt-1">
                    {thread.snippet || 'No messages yet.'}
                  </div>
                  {isActive && (
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] uppercase tracking-wide text-primary font-semibold">
                        Active
                      </span>
                      {messageCount > 0 && (
                        <span className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full bg-primary/15 text-primary text-[10px] font-semibold">
                          {messageCount}
                        </span>
                      )}
                    </div>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="rounded-xl border border-dashed border-border px-3 py-3 text-xs text-muted">
          Start a conversation to see it here.
        </div>
      )}
    </div>

    <div className="bg-surface-hover rounded-xl border border-border p-4 text-xs text-muted">
      <p className="font-medium text-text mb-2">Helpful Tips</p>
      <p>Ask for steps, examples, or a short summary.</p>
      <p className="mt-2">Mention a grade level to simplify answers.</p>
    </div>

    {isAdmin && (
      <div className="bg-surface-hover rounded-xl border border-border p-4 text-xs text-muted space-y-3">
        <div>
          <p className="text-muted">Total Tokens</p>
          <p className="text-lg font-semibold text-text">{totalTokens}</p>
        </div>
        <div>
          <p className="text-muted">Messages</p>
          <p className="text-lg font-semibold text-text">{messageCount}</p>
        </div>
        <Link href="/admin/logs" className="text-primary hover:underline text-sm">
          View admin logs
        </Link>
      </div>
    )}
  </aside>
);

export default ChatSidebar;
