import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import { fontVariables } from '@/theme/fonts';
import Providers from './providers';

// Global CSS — App Router allows global stylesheet imports in the root layout.
import '@/index.css';
import 'highlight.js/styles/github-dark.css';

export const metadata: Metadata = {
  icons: {
    icon: '/favicon.ico',
    apple: '/GoblinOSIcon.png',
  },
  manifest: '/site.webmanifest',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#161008',
  // Without viewportFit=cover every `env(safe-area-inset-*)` in the app resolves
  // to 0 on iOS, so the home indicator overlaps fixed UI (e.g. the chat composer).
  viewportFit: 'cover',
  // On-screen keyboard shrinks the layout viewport (Chromium/Android) so pinned
  // composers stay visible. iOS ignores this — see useVisualViewportHeight.
  interactiveWidget: 'resizes-content',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={fontVariables}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
