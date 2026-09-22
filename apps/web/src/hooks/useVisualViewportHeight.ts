'use client';

import { useEffect } from 'react';

/**
 * Publishes the *visual* viewport height as `--vvh` on `<html>`, which
 * `.chat-viewport` consumes (see `src/index.css`).
 *
 * Why: the chat shell must shrink when the on-screen keyboard opens so the
 * composer stays reachable. `interactiveWidget: 'resizes-content'` (see
 * `app/layout.tsx`) does this on Chromium/Android, but iOS Safari only shrinks
 * the *visual* viewport and leaves the layout viewport — and therefore `100dvh`
 * — alone. A pinned composer then ends up underneath the keyboard.
 *
 * The variable is written with `setProperty` rather than a JSX inline style
 * object, because `tooling/quality/guard-no-inline-styles.js` disallows inline
 * style objects in this app. Updates are skipped while the user is pinch-zoomed
 * (`scale > 1`) so the shell does not collapse mid-zoom.
 */
export function useVisualViewportHeight(): void {
  useEffect(() => {
    const viewport = window.visualViewport;
    const root = document.documentElement;
    if (!viewport) return;

    const sync = () => {
      if (viewport.scale > 1) return;
      root.style.setProperty('--vvh', `${Math.round(viewport.height)}px`);
    };

    sync();
    viewport.addEventListener('resize', sync);

    return () => {
      viewport.removeEventListener('resize', sync);
      root.style.removeProperty('--vvh');
    };
  }, []);
}
