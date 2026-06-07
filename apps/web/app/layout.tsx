import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import { fontVariables } from '@/theme/fonts';
import Providers from './providers';

// Global CSS — App Router allows global stylesheet imports in the root layout.
import '@/index.css';
import 'highlight.js/styles/github-dark.css';

// Every route was previously rendered with a no-op getServerSideProps (always
// dynamic, never statically generated). Forcing dynamic here preserves that
// behaviour for the whole app and avoids the static-prerender requirement for
// `useSearchParams()` in the client screens.
export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  icons: {
    icon: '/favicon.svg',
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
