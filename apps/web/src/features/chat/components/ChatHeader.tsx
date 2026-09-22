'use client';

import Link from 'next/link';
import { AlertCircle, LayoutDashboard, PanelRightOpen, Search, X } from 'lucide-react';
import { useHealthCheck } from '../../../hooks/useHealthCheck';
import type { HealthStatus } from '../../../types/api';

type MobileChatPanelTab = 'conversations' | 'preview';

/**
 * Icon-only at `md` and below (44px touch target), icon + label above it.
 *
 * The label is always rendered in its own `<span>` and merely hidden with CSS
 * below `md`. That keeps it out of the visual layout on phones while leaving it
 * in the DOM and accessible name, and it keeps each label as exactly one text
 * node so `getByText` stays unambiguous.
 */
const HEADER_ICON_BUTTON =
  'inline-flex items-center justify-center gap-2 rounded-lg ' +
  'h-11 w-11 md:h-auto md:w-auto md:px-3 md:py-2';

interface ChatHeaderProps {
  /** Show admin-only shortcuts when true. */
  isAdmin: boolean;
  /** Handler for clearing the current chat. */
  onClear: () => void;
  /** Toggle unified mobile chat panel. */
  onToggleMobilePanel?: () => void;
  /** Whether unified mobile chat panel is open. */
  isMobilePanelOpen?: boolean;
  /** Active tab inside unified mobile panel. */
  activeMobilePanelTab?: MobileChatPanelTab;
  /** Show unified mobile panel toggle button. */
  showMobilePanelToggle?: boolean;
}

const ConnectionStatus = ({ health }: { health: HealthStatus | null }) => {
  if (!health) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-hover px-3 py-1 text-xs text-muted">
        <span className="h-2 w-2 rounded-full bg-gray-400 animate-pulse" />
        <span className="hidden sm:inline">Loading...</span>
      </span>
    );
  }

  const statusConfig = {
    healthy: { color: 'bg-success', text: 'Live gateway' },
    degraded: { color: 'bg-warning', text: 'Degraded' },
    warnings: { color: 'bg-warning', text: 'Warnings' },
  } as const;

  const overall = health.overall ?? health.status;
  const config = statusConfig[overall as keyof typeof statusConfig] || {
    color: 'bg-error',
    text: 'Offline',
  };

  return (
    <span
      className="inline-flex items-center gap-2 rounded-full border border-border bg-surface-hover px-3 py-1 text-xs text-muted"
      title={config.text}
    >
      <span className={`h-2 w-2 rounded-full ${config.color}`} />
      <span className="hidden sm:inline">{config.text}</span>
    </span>
  );
};

const ChatHeader = ({
  isAdmin,
  onClear,
  onToggleMobilePanel,
  isMobilePanelOpen = false,
  activeMobilePanelTab = 'conversations',
  showMobilePanelToggle = false,
}: ChatHeaderProps) => {
  const healthQuery = useHealthCheck();
  const health = healthQuery.data ?? null;

  return (
    <header className="sticky top-0 z-20 border-b border-border/70 bg-surface/85 backdrop-blur px-3 pt-[max(0.5rem,env(safe-area-inset-top))] pb-2 md:px-6 md:py-4">
      {/* Single row on mobile so the message list keeps the remaining height. */}
      <div className="flex flex-wrap items-center gap-x-2 gap-y-2 md:gap-x-3">
        <h1 className="shrink-0 my-0 text-base md:text-2xl font-semibold text-text">
          <span className="md:hidden">Goblin</span>
          <span className="hidden md:inline">AI Orchestration Console</span>
        </h1>

        <ConnectionStatus health={health} />

        <p className="hidden lg:block text-sm text-muted truncate">
          Route requests, optimize costs, monitor reliability. Control the LLM ecosystem end-to-end.
        </p>

        <div className="ml-auto flex shrink-0 items-center gap-1.5 md:gap-2">
          {showMobilePanelToggle && onToggleMobilePanel ? (
            <button
              type="button"
              onClick={onToggleMobilePanel}
              className={`${HEADER_ICON_BUTTON} lg:hidden border border-border bg-surface hover:bg-surface-hover text-text`}
              aria-label={isMobilePanelOpen ? 'Close chat panel' : 'Open chat panel'}
              aria-expanded={isMobilePanelOpen ? 'true' : 'false'}
            >
              {isMobilePanelOpen ? (
                <X className="h-4 w-4" />
              ) : (
                <PanelRightOpen className="h-4 w-4" />
              )}
              <span className="hidden md:inline">
                {activeMobilePanelTab === 'preview' ? 'Preview' : 'Conversations'}
              </span>
            </button>
          ) : null}

          {/* Clear lives in the composer on mobile; duplicated here for desktop. */}
          <button
            onClick={onClear}
            type="button"
            className="hidden md:inline-flex items-center justify-center rounded-lg border border-border px-3 py-2 text-text hover:bg-surface-hover"
          >
            <span>Clear Chat</span>
          </button>

          <Link
            href="/search"
            aria-label="Global Search"
            className={`${HEADER_ICON_BUTTON} bg-primary/15 text-primary hover:bg-primary/25`}
          >
            <Search className="h-4 w-4" aria-hidden="true" />
            <span className="hidden md:inline">Global Search</span>
          </Link>

          {isAdmin && (
            <Link
              href="/admin"
              aria-label="Admin Dashboard"
              className={`${HEADER_ICON_BUTTON} bg-surface-hover text-text hover:bg-surface-active`}
            >
              <LayoutDashboard className="h-4 w-4" aria-hidden="true" />
              <span className="hidden md:inline">Admin Dashboard</span>
            </Link>
          )}

          {isAdmin && (
            <Link
              href="/debug/connectivity"
              aria-label="Debug connectivity"
              title="Debug connectivity"
              className={`${HEADER_ICON_BUTTON} bg-surface-hover text-text hover:bg-surface-active`}
            >
              <AlertCircle className="h-4 w-4" aria-hidden="true" />
            </Link>
          )}
        </div>
      </div>
    </header>
  );
};

export default ChatHeader;
