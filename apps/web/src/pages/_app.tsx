import type { AppProps } from 'next/app';
import { useEffect, useState, useRef } from 'react';
import { useRouter } from 'next/router';
import { QueryClientProvider } from '@tanstack/react-query';
import { Analytics } from '@vercel/analytics/react';
import { ToastProvider, useToast } from '../contexts/ToastContext';
import { ProviderProvider } from '../contexts/ProviderContext';
import { ContrastModeProvider } from '../hooks/useContrastMode';
import AuthBootstrapper from '../auth/AuthBootstrapper';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { ToastContainer } from '../components/ToastContainer';
import { RouteBoundaryFallback, formatBoundaryTechnicalDetail } from '../components/RouteBoundary';
import { createQueryClient } from '../lib/queryClient';
import { initGA } from '../utils/analytics';
import { setupGlobalErrorTracking, monitorNetworkStatus } from '../utils/error-tracking';
import { reportWebVitalMetric } from '../utils/web-vitals';
import { useUIStore } from '../store/uiStore';
import { extractApiErrorMessage } from '../lib/api/shared';

// Import global CSS files - Next.js only allows global CSS imports in _app.tsx
import '../index.css';
import 'highlight.js/styles/github-dark.css';
import ChatFAB from '../components/ChatFAB';
import StatusBar from '../components/StatusBar';
import PageTransition from '../components/PageTransition';

/**
 * Bridge component to sync global UI store notifications with the Toast system.
 * This enables non-React code (like API interceptors) to trigger toasts via Zustand.
 */
function NotificationBridge() {
  const { addToast } = useToast();
  const notifications = useUIStore((state) => state.notifications);
  const lastId = useRef<string | null>(null);

  useEffect(() => {
    const latest = notifications[notifications.length - 1];
    if (latest && latest.id !== lastId.current) {
      addToast({
        type: latest.type,
        title: latest.title,
        message: latest.message,
        duration: latest.duration,
      });
      lastId.current = latest.id;
    }
  }, [notifications, addToast]);

  return null;
}

export default function App({ Component, pageProps }: AppProps) {
  const [queryClient] = useState(() => createQueryClient());
  const router = useRouter();

  useEffect(() => {
    initGA();
    setupGlobalErrorTracking();
    monitorNetworkStatus();

    // Automatically trigger error toasts for failed TanStack Query mutations
    const unsubscribe = queryClient.getMutationCache().subscribe((event) => {
      if (event.type === 'updated' && event.action.type === 'error') {
        const error = event.action.error as any;
        useUIStore.getState().addNotification({
          type: 'error',
          title: 'Action failed',
          message: extractApiErrorMessage(
            error?.response?.data,
            error?.message || 'Request failed'
          ),
        });
      }
    });

    return () => unsubscribe();
  }, [queryClient]);

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
              <NotificationBridge />
              <a href="#main-content" className="skip-link">
                Skip to main content
              </a>
              <PageTransition routeKey={router.asPath}>
                <Component {...pageProps} />
              </PageTransition>
              <ToastContainer />
              <ChatFAB />
              <StatusBar />
              <Analytics />
            </ContrastModeProvider>
          </ProviderProvider>
        </ToastProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export { reportWebVitalMetric as reportWebVitals };
