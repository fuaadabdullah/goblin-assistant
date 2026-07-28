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
  themeColor: '#161008',
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
