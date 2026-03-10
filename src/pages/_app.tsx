import type { AppProps } from 'next/app';
import { useEffect, useState } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { Analytics } from '@vercel/analytics/react';
import { ToastProvider } from '../contexts/ToastContext';
import { ProviderProvider } from '../contexts/ProviderContext';
import { ContrastModeProvider } from '../hooks/useContrastMode';
import AuthBootstrapper from '../auth/AuthBootstrapper';
import { ErrorBoundary } from '../components/ErrorBoundary';
import {
  RouteBoundaryFallback,
  formatBoundaryTechnicalDetail,
} from '../components/RouteBoundary';
import { createQueryClient } from '../lib/queryClient';
import { initGA } from '../utils/analytics';
import { setupGlobalErrorTracking, monitorNetworkStatus } from '../utils/error-tracking';

// Import global CSS files - Next.js only allows global CSS imports in _app.tsx
import '../index.css';
import 'highlight.js/styles/github-dark.css';

export default function App({ Component, pageProps }: AppProps) {
  const [queryClient] = useState(() => createQueryClient());

  useEffect(() => {
    initGA();
    setupGlobalErrorTracking();
    monitorNetworkStatus();
  }, []);

  return (
    <ErrorBoundary
      boundaryName="app-shell"
      fallbackRender={({ error, errorId }) => (
        <RouteBoundaryFallback
          title="Goblin Assistant could not finish loading"
          description="A render failure interrupted the application shell before this page became usable."
          actions={[
            { type: 'link', label: 'Go Home', href: '/', variant: 'primary' },
            { type: 'copyErrorId', label: 'Copy Error ID', variant: 'secondary' },
            { type: 'reload', label: 'Reload App', variant: 'secondary' },
          ]}
          errorId={errorId}
          technicalDetail={formatBoundaryTechnicalDetail(error)}
        />
      )}
    >
      <QueryClientProvider client={queryClient}>
        <AuthBootstrapper />
        <ToastProvider>
          <ProviderProvider>
            <ContrastModeProvider>
              <a href="#main-content" className="skip-link">
                Skip to main content
              </a>
              <Component {...pageProps} />
              <Analytics />
            </ContrastModeProvider>
          </ProviderProvider>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
