'use client';

import Link from 'next/link';
import { PanelRight, X, SlidersHorizontal } from 'lucide-react';
import { useHealth } from '../../../hooks/api/useHealth';
import { useUIStore } from '../../../store/uiStore';

type MobileChatPanelTab = 'conversations' | 'preview';

interface ChatHeaderProps {
  isAdmin: boolean;
  onClear: () => void;
  onToggleMobilePanel?: () => void;
  isMobilePanelOpen?: boolean;
  activeMobilePanelTab?: MobileChatPanelTab;
  showMobilePanelToggle?: boolean;
}

function StatusDot({ health }: { health: { overall: string } | null }) {
  if (!health) {
    return <span className="h-1.5 w-1.5 rounded-full bg-muted/50 animate-pulse" />;
  }
  const overall = health.overall;
  const color =
    overall === 'healthy'
      ? 'bg-success'
      : overall === 'degraded' || overall === 'warnings'
        ? 'bg-warning'
        : 'bg-error';
  const label =
    overall === 'healthy' ? 'Live' : overall === 'degraded' ? 'Degraded' : 'Offline';

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted">
      <span className={`h-1.5 w-1.5 rounded-full ${color}`} />
      {label}
    </span>
  );
}

const ChatHeader = ({
  isAdmin,
  onClear,
  onToggleMobilePanel,
  isMobilePanelOpen = false,
  activeMobilePanelTab = 'conversations',
  showMobilePanelToggle = false,
}: ChatHeaderProps) => {
  const healthQuery = useHealth();
  const health = healthQuery.data ?? null;
  const toggleInspector = useUIStore((s) => s.toggleChatInspector);
  const inspectorOpen = useUIStore((s) => s.chatInspectorOpen);

  return (
    <header className="sticky top-0 z-20 border-b border-border/60 bg-surface/80 backdrop-blur">
      <div className="flex items-center justify-between gap-3 px-4 py-2.5">
        <div className="flex items-center gap-2">
          {showMobilePanelToggle && onToggleMobilePanel && (
            <button
              type="button"
              onClick={onToggleMobilePanel}
              className="lg:hidden p-2 rounded-lg text-muted hover:text-text hover:bg-surface-hover transition-colors"
              aria-label={isMobilePanelOpen ? 'Close sidebar' : 'Open sidebar'}
              aria-expanded={isMobilePanelOpen}
            >
              {isMobilePanelOpen ? (
                <X className="w-4 h-4" />
              ) : (
                <PanelRight className="w-4 h-4 rotate-180" />
              )}
              <span className="sr-only">
                {activeMobilePanelTab === 'preview' ? 'Preview' : 'Conversations'}
              </span>
            </button>
          )}
          <StatusDot health={health} />
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onClear}
            className="px-3 py-1.5 rounded-lg text-xs text-muted hover:text-text hover:bg-surface-hover border border-transparent hover:border-border/60 transition-colors"
          >
            New chat
          </button>

          {isAdmin && (
            <>
              <Link
                href="/search"
                className="px-3 py-1.5 rounded-lg text-xs text-muted hover:text-text hover:bg-surface-hover transition-colors"
              >
                Search
              </Link>
              <Link
                href="/admin"
                className="px-3 py-1.5 rounded-lg text-xs text-muted hover:text-text hover:bg-surface-hover transition-colors"
              >
                Admin
              </Link>
            </>
          )}

          <button
            type="button"
            onClick={toggleInspector}
            className={`p-2 rounded-lg transition-colors ${
              inspectorOpen
                ? 'text-primary bg-primary/10'
                : 'text-muted hover:text-text hover:bg-surface-hover'
            }`}
            aria-label="Toggle inspector"
            aria-pressed={inspectorOpen}
            title="Inspector"
          >
            <SlidersHorizontal className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};

export default ChatHeader;
