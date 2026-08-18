'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import { apiClient } from '@/lib/api';

type State = 'idle' | 'open' | 'sending' | 'done';

const QUICK_TAGS = [
  { id: 'what-is-goblin', label: 'What is a Goblin?' },
  { id: 'which-model', label: 'Which model am I using?' },
  { id: 'did-it-remember', label: 'Did it remember that?' },
  { id: 'too-slow', label: 'Why is this slow?' },
  { id: 'vs-chatgpt', label: 'Better than ChatGPT how?' },
  { id: 'other', label: 'Something else' },
];

export default function BetaSignal() {
  const [state, setState] = useState<State>('idle');
  const [note, setNote] = useState('');
  const [tag, setTag] = useState('');
  const pathname = usePathname();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (state !== 'open') return;
    function handleClick(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setState('idle');
        setNote('');
        setTag('');
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [state]);

  // Focus textarea when panel opens
  useEffect(() => {
    if (state === 'open') {
      setTimeout(() => textareaRef.current?.focus(), 60);
    }
  }, [state]);

  // Auto-reset after "done"
  useEffect(() => {
    if (state !== 'done') return;
    const t = setTimeout(() => {
      setState('idle');
      setNote('');
      setTag('');
    }, 2200);
    return () => clearTimeout(t);
  }, [state]);

  async function submit() {
    if (state === 'sending') return;
    setState('sending');
    try {
      await apiClient.submitBetaSignal({
        page: pathname ?? '/',
        note: note.trim() || undefined,
        tag: tag || undefined,
      });
    } catch {
      // swallow — signal capture should never interrupt the user
    }
    setState('done');
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') {
      setState('idle');
      setNote('');
      setTag('');
    }
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      submit();
    }
  }

  return (
    <div className="fixed bottom-20 left-4 z-50" ref={panelRef}>
      {/* Trigger button */}
      {state === 'idle' && (
        <button
          onClick={() => setState('open')}
          title="Something confusing? Tell us."
          className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-card text-muted-foreground shadow-sm transition-all hover:border-primary hover:text-primary hover:shadow-md"
          aria-label="Report confusion"
        >
          <span className="text-sm font-semibold leading-none">?</span>
        </button>
      )}

      {/* Done state */}
      {state === 'done' && (
        <div className="flex h-8 w-8 items-center justify-center rounded-full border border-green-500/40 bg-green-500/10 text-green-600 shadow-sm">
          <span className="text-sm">✓</span>
        </div>
      )}

      {/* Open panel */}
      {(state === 'open' || state === 'sending') && (
        <div
          className="absolute bottom-10 left-0 w-72 rounded-xl border border-border bg-card shadow-xl"
          onKeyDown={handleKeyDown}
        >
          <div className="border-b border-border px-4 py-3">
            <p className="text-sm font-semibold text-foreground">Something confusing?</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Tap what hit you — no judgment, no form.
            </p>
          </div>

          {/* Quick tags */}
          <div className="flex flex-wrap gap-1.5 px-4 py-3">
            {QUICK_TAGS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTag(tag === t.id ? '' : t.id)}
                className={`rounded-full border px-2.5 py-1 text-xs transition-colors ${
                  tag === t.id
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-border bg-muted/50 text-muted-foreground hover:border-primary/50 hover:text-foreground'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Optional note */}
          <div className="px-4 pb-3">
            <textarea
              ref={textareaRef}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="More detail? (optional)"
              rows={2}
              className="w-full resize-none rounded-lg border border-border bg-background px-3 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
            />
            <div className="mt-2 flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground">⌘↵ to send</span>
              <button
                onClick={submit}
                disabled={state === 'sending' || (!tag && !note.trim())}
                className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground transition-opacity disabled:opacity-40"
              >
                {state === 'sending' ? 'Sending…' : 'Send'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
