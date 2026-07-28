import { useState, useMemo } from 'react';
import Link from 'next/link';
import { Search, X, Plus } from 'lucide-react';
import type { ChatThread } from '../types';

interface ChatSidebarProps {
  threads: ChatThread[];
  isThreadsLoading: boolean;
  activeThreadKey: string | null;
  onSelectThread: (threadKey: string) => void;
  onNewConversation: () => void;
  isAdmin: boolean;
  totalTokens: number;
  messageCount: number;
  className?: string;
}

const CATEGORY_COLORS: Record<string, string> = {
  coding: 'bg-blue-500/15 text-blue-600',
  trading: 'bg-emerald-500/15 text-emerald-700',
  finance: 'bg-yellow-500/15 text-yellow-700',
  health: 'bg-rose-500/15 text-rose-600',
  relationships: 'bg-purple-500/15 text-purple-600',
  research: 'bg-slate-500/15 text-slate-600',
};

type ThreadGroup = { label: string; threads: ChatThread[] };

function groupByDate(threads: ChatThread[]): ThreadGroup[] {
  const now = new Date();
  const startOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const today = startOf(now);
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const weekAgo = new Date(today);
  weekAgo.setDate(today.getDate() - 7);

  const groups: ThreadGroup[] = [
    { label: 'Today', threads: [] },
    { label: 'Yesterday', threads: [] },
    { label: 'This Week', threads: [] },
    { label: 'Older', threads: [] },
  ];

  for (const t of threads) {
    const d = startOf(new Date(t.updatedAt ?? t.createdAt));
    if (d >= today) groups[0]!.threads.push(t);
    else if (d >= yesterday) groups[1]!.threads.push(t);
    else if (d >= weekAgo) groups[2]!.threads.push(t);
    else groups[3]!.threads.push(t);
  }

  return groups.filter((g) => g.threads.length > 0);
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
}: ChatSidebarProps) => {
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return threads;
    return threads.filter(
      (t) =>
        (t.title ?? '').toLowerCase().includes(q) ||
        (t.snippet ?? '').toLowerCase().includes(q)
    );
  }, [threads, search]);

  const groups = useMemo(() => groupByDate(filtered), [filtered]);

  return (
    <aside
      className={`flex w-64 flex-shrink-0 border-r border-border bg-surface flex-col ${className}`}
    >
      <div className="px-3 pt-4 pb-2 flex-shrink-0">
        <button
          type="button"
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-sm font-medium bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      <div className="px-3 pb-3 flex-shrink-0">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted pointer-events-none" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search conversations…"
            className="w-full pl-8 pr-7 py-1.5 text-xs bg-surface-hover border border-border/60 rounded-lg text-text placeholder-muted focus:outline-none focus:border-primary/40 focus:ring-1 focus:ring-primary/20 transition"
            aria-label="Search conversations"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch('')}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-text"
              aria-label="Clear search"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3 space-y-4 min-h-0">
        {isThreadsLoading ? (
          <div className="space-y-2 px-1 animate-pulse">
            {[1, 2, 3].map((n) => (
              <div key={n} className="rounded-xl border border-border bg-bg px-3 py-3 space-y-2">
                <div className="h-3 w-20 bg-surface-hover rounded" />
                <div className="h-4 w-full bg-surface-hover rounded" />
                <div className="h-3 w-3/4 bg-surface-hover rounded" />
              </div>
            ))}
          </div>
        ) : groups.length > 0 ? (
          groups.map((group) => (
            <div key={group.label}>
              <p className="px-2 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted/70">
                {group.label}
              </p>
              <ul className="space-y-0.5">
                {group.threads.map((thread) => {
                  const isActive = thread.threadKey === activeThreadKey;
                  return (
                    <li key={thread.threadKey}>
                      <button
                        type="button"
                        onClick={() => onSelectThread(thread.threadKey)}
                        aria-current={isActive ? 'true' : undefined}
                        className={`w-full text-left rounded-xl px-3 py-2.5 transition-colors ${
                          isActive
                            ? 'bg-primary/10 text-text'
                            : 'text-text hover:bg-surface-hover'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-sm font-medium line-clamp-1 flex-1">
                            {thread.title || 'Untitled'}
                          </span>
                          {isActive && (
                            <span className="w-1.5 h-1.5 rounded-full bg-primary mt-1.5 flex-shrink-0" />
                          )}
                        </div>
                        <p className="text-[11px] text-muted line-clamp-1 mt-0.5">
                          {thread.snippet || 'No messages yet'}
                        </p>
                        {thread.category && (
                          <span
                            className={`inline-block mt-1 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide ${CATEGORY_COLORS[thread.category] ?? 'bg-surface-hover text-muted'}`}
                          >
                            {thread.category}
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))
        ) : (
          <div className="px-3 py-6 text-center">
            <p className="text-xs text-muted">
              {search ? 'No conversations match your search.' : 'Start a conversation to see it here.'}
            </p>
          </div>
        )}
      </div>

      <div className="border-t border-border/60 px-3 py-3 flex-shrink-0 space-y-2">
        {isAdmin && (
          <div className="grid grid-cols-2 gap-2 text-xs text-muted">
            <div>
              <p className="text-[10px] uppercase tracking-wide text-muted/70">Tokens</p>
              <p className="font-semibold text-text">{totalTokens.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wide text-muted/70">Messages</p>
              <p className="font-semibold text-text">{messageCount}</p>
            </div>
            <Link
              href="/admin/logs"
              className="col-span-2 text-primary hover:underline text-xs mt-1"
            >
              Admin logs →
            </Link>
          </div>
        )}
      </div>
    </aside>
  );
};

export default ChatSidebar;
