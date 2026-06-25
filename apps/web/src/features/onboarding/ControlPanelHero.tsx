import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import StatusIndicator from '../../components/StatusIndicator';
import { useSystemStatus } from '../../hooks/useSystemStatus';
import { trackEvent } from '../../utils/analytics';

const ROTATING = ['Finance', 'Code', 'Learning', 'Trading systems', 'Decision support'] as const;

export default function ControlPanelHero() {
  const { status, loading, refresh } = useSystemStatus({
    pollIntervalMs: 15000,
  });
  const words = useMemo(() => ROTATING, []);
  const [index, setIndex] = useState(0);

  // Track hero impression on mount
  useEffect(() => {
    trackEvent('control_panel_hero_view', {
      status_models: status.models,
      status_routing: status.routing,
      status_sandbox: status.sandbox,
    });
  }, [status.models, status.routing, status.sandbox]);

  // Track when user manually refreshes
  const handleRefresh = () => {
    trackEvent('control_panel_hero_refresh_click', {
      current_status: JSON.stringify(status),
    });
    refresh();
  };

  // Track action clicks
  const trackAction = (action: string) => {
    trackEvent('control_panel_hero_action', {
      action,
      domain: words[index]!,
    });
  };

  useEffect(() => {
    const prefersReduced = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches;
    if (prefersReduced) return undefined;
    const id = setInterval(() => setIndex((i) => (i + 1) % words.length), 3000);
    return () => clearInterval(id);
  }, [words.length]);

  const current = words[index];

  return (
    <section className="bg-surface/80 border border-border rounded-3xl p-6 mb-8 shadow-card backdrop-blur">
      <div className="flex items-start justify-between gap-6">
        <div className="flex-1">
          <h1 className="text-3xl font-semibold text-text mb-1">Control panel</h1>
          <p className="text-sm text-muted mb-4">
            Live status and quick actions — this system is running.
          </p>

          <div className="flex items-center gap-4 mb-4 flex-wrap">
            <div className="flex gap-3 items-center">
              <StatusIndicator label="Models" status={status.models ?? 'unknown'} />
              <StatusIndicator label="Routing" status={status.routing ?? 'unknown'} />
              <StatusIndicator label="Sandbox" status={status.sandbox ?? 'unknown'} />
            </div>
            <button
              type="button"
              onClick={handleRefresh}
              className="px-3 py-1 rounded-md bg-surface-hover border border-border text-sm text-text hover:bg-surface-active"
              aria-label="Refresh system status"
            >
              Refresh status
            </button>
          </div>

          <div className="mb-4">
            <div className="text-sm text-muted mb-1">Currently running:</div>
            <div className="flex items-center gap-3">
              <div className="text-lg font-mono text-primary">{current}</div>
              <div className="text-sm text-muted">
                — Live examples and demos tailored to the domain above.
              </div>
            </div>
            <div className="sr-only" aria-live="polite">{`Rotating category ${current}`}</div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              href="/chat?guest=1"
              onClick={() => trackAction('try_guest_chat')}
              className="px-4 py-2 rounded-lg bg-primary text-text-inverse font-medium shadow-glow-primary hover:brightness-110"
            >
              Try for free
            </Link>
            <Link
              href="/search"
              onClick={() => trackAction('audit_logs')}
              className="px-4 py-2 rounded-lg bg-primary/15 text-text border border-border hover:bg-primary/20 font-medium"
            >
              Audit Logs
            </Link>
            <Link
              href="/help"
              onClick={() => trackAction('documentation')}
              className="px-4 py-2 rounded-lg bg-surface-hover text-text border border-border hover:bg-surface-active font-medium"
            >
              Documentation
            </Link>
          </div>
        </div>

        <div className="w-56 shrink-0">
          <div className="rounded-2xl border border-border bg-bg p-4 shadow-inner">
            <div className="text-xs font-mono uppercase tracking-wide text-muted mb-2">Preview</div>
            <div className="text-sm text-text">
              {loading ? 'Loading status...' : `Updated ${status.updatedAt ?? 'just now'}`}
            </div>
            <div className="mt-3">
              <div className="rounded-xl bg-surface border border-border p-3">
                <div className="text-[11px] uppercase tracking-wide text-muted font-semibold mb-1">
                  Example
                </div>
                <p className="text-sm text-text">
                  Try a quick demo in the chat for {current} scenarios.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
