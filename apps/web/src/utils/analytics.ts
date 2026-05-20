/**
 * Google Analytics 4 (gtag.js) integration.
 *
 * Loads the GA4 script dynamically at runtime — no npm package required.
 * No-op when NEXT_PUBLIC_GA_MEASUREMENT_ID is not set or on the server.
 */

import { env } from '../config/env';

declare global {
  interface Window {
    dataLayer: unknown[];
    gtag: (...args: unknown[]) => void;
  }
}

let initialized = false;

export function initGA(): void {
  if (initialized) return;
  if (typeof window === 'undefined') return;
  if (!env.gaMeasurementId) return;

  const id = env.gaMeasurementId;

  // gtag.js bootstrap
  const script = document.createElement('script');
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`;
  document.head.appendChild(script);

  window.dataLayer = window.dataLayer || [];
  window.gtag = function gtag() {
    // eslint-disable-next-line prefer-rest-params
    window.dataLayer.push(arguments);
  };
  window.gtag('js', new Date());
  window.gtag('config', id, { send_page_view: true });

  initialized = true;
}

export function trackEvent(
  name: string,
  params?: Record<string, string | number | boolean>,
): void {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', name, params);
  }
}
