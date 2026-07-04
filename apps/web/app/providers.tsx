'use client';

import type { ReactNode } from 'react';
import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { QueryClientProvider } from '@tanstack/react-query';
import { Analytics } from '@vercel/analytics/react';
import { datadogRum } from '@datadog/browser-rum';
import { datadogLogs } from '@datadog/browser-logs';
import { ProviderProvider } from '@/contexts/ProviderContext';
import { ContrastModeProvider } from '@/hooks/useContrastMode';
import AuthBootstrapper from '@/auth/AuthBootstrapper';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { RouteBoundaryFallback, formatBoundaryTechnicalDetail } from '@/components/RouteBoundary';
import { createQueryClient } from '@/lib/queryClient';
import { initGA } from '@/utils/analytics';
import { setupGlobalErrorTracking, monitorNetworkStatus } from '@/utils/error-tracking';
import ChatFAB from '@/components/ChatFAB';
import StatusBar from '@/components/StatusBar';
import PageTransition from '@/components/PageTransition';

function sanitizeDatadogTagValue(value: string | undefined, fallback?: string): string | undefined {
  const normalized = value?.trim().replace(/[^a-zA-Z0-9_-]+/g, '-').replace(/-+/g, '-').replace(/^[-_]+|[-_]+$/g, '');
  if (normalized) return normalized;
  return fallback;
}

function shouldLoadProviderRegistry(pathname: string | null): boolean {
  if (!pathname) return true;
  return !['/login', '/register'].some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );
}

function shouldRenderAnalytics(): boolean {
  return process.env['VERCEL_ENV'] === 'production';
}

function initDatadog() {
  const appId = process.env['NEXT_PUBLIC_DD_APPLICATION_ID'];
  const clientToken = process.env['NEXT_PUBLIC_DD_CLIENT_TOKEN'];
  if (!appId || !clientToken) return;

  const site = process.env['NEXT_PUBLIC_DD_SITE'] ?? 'datadoghq.com';
  const env = sanitizeDatadogTagValue(process.env['NEXT_PUBLIC_DD_ENV'] ?? process.env['NODE_ENV'], 'development');
  const version = sanitizeDatadogTagValue(process.env['NEXT_PUBLIC_DD_VERSION'], '0');

  datadogRum.init({
    applicationId: appId,
    clientToken,
    site,
    service: 'goblin-web',
    env,
    version,
    sessionSampleRate: 100,
    sessionReplaySampleRate: 10,
    trackUserInteractions: true,
    trackResources: true,
    trackLongTasks: true,
    defaultPrivacyLevel: 'mask-user-input',
  });

  datadogLogs.init({
    clientToken,
    site,
    service: 'goblin-web',
    env,
    version,
    forwardErrorsToLogs: true,
    sessionSampleRate: 100,
  } as any);
}

export default function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(() => createQueryClient());
  const pathname = usePathname();
  const enableProviderRegistry = shouldLoadProviderRegistry(pathname);
  const enableAnalytics = shouldRenderAnalytics();

  useEffect(() => {
    initDatadog();
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
        <ProviderProvider enableRegistry={enableProviderRegistry}>
          <ContrastModeProvider>
            <a href="#main-content" className="skip-link">
              Skip to main content
            </a>
            <PageTransition routeKey={pathname ?? '/'}>{children}</PageTransition>
            <ChatFAB />
            <StatusBar />
            {enableAnalytics ? <Analytics /> : null}
          </ContrastModeProvider>
        </ProviderProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}
