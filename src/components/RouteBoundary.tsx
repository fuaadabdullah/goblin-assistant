import type { ComponentType } from 'react';
import { useState } from 'react';
import { env } from '../config/env';
import {
  ErrorBoundary,
  type ErrorBoundaryRenderProps,
} from './ErrorBoundary';

export type RouteBoundaryAction =
  | { type: 'link'; label: string; href: string; variant?: 'primary' | 'secondary' }
  | { type: 'copyErrorId'; label: string; variant?: 'primary' | 'secondary' }
  | { type: 'reload'; label: string; variant?: 'primary' | 'secondary' };

export interface RouteBoundaryFallbackProps {
  title: string;
  description: string;
  actions: RouteBoundaryAction[];
  errorId?: string;
  technicalDetail?: string;
}

export type RouteBoundaryKey =
  | 'home'
  | 'account'
  | 'chat'
  | 'googleCallback'
  | 'help'
  | 'login'
  | 'register'
  | 'sandbox'
  | 'search'
  | 'settings'
  | 'startup'
  | 'notFound'
  | 'adminIndex'
  | 'adminLogs'
  | 'adminProviders'
  | 'adminSettings';

type RouteBoundaryConfig = Omit<RouteBoundaryFallbackProps, 'errorId' | 'technicalDetail'>;

const primaryButtonClass =
  'inline-flex items-center justify-center rounded-lg bg-primary px-4 py-2 text-sm font-medium text-text-inverse shadow-glow-primary hover:brightness-110';
const secondaryButtonClass =
  'inline-flex items-center justify-center rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-text hover:bg-surface-hover';

const adminConfig = (title: string, description: string): RouteBoundaryConfig => ({
  title,
  description,
  actions: [
    { type: 'link', label: 'Back to Admin', href: '/admin', variant: 'primary' },
    { type: 'link', label: 'Go Home', href: '/', variant: 'secondary' },
    { type: 'copyErrorId', label: 'Copy Error ID', variant: 'secondary' },
  ],
});

const authConfig = (title: string, description: string): RouteBoundaryConfig => ({
  title,
  description,
  actions: [
    { type: 'link', label: 'Sign In Again', href: '/login', variant: 'primary' },
    { type: 'link', label: 'Go Home', href: '/', variant: 'secondary' },
  ],
});

const workspaceConfig = (title: string, description: string): RouteBoundaryConfig => ({
  title,
  description,
  actions: [
    { type: 'link', label: 'Go Home', href: '/', variant: 'primary' },
    { type: 'link', label: 'Open Help', href: '/help', variant: 'secondary' },
    { type: 'copyErrorId', label: 'Copy Error ID', variant: 'secondary' },
  ],
});

const generalConfig = (title: string, description: string): RouteBoundaryConfig => ({
  title,
  description,
  actions: [
    { type: 'link', label: 'Go Home', href: '/', variant: 'primary' },
    { type: 'link', label: 'Open Help', href: '/help', variant: 'secondary' },
    { type: 'copyErrorId', label: 'Copy Error ID', variant: 'secondary' },
  ],
});

const routeBoundaryConfig: Record<RouteBoundaryKey, RouteBoundaryConfig> = {
  home: generalConfig(
    'Home is temporarily unavailable',
    'Goblin Assistant failed while rendering the home experience.'
  ),
  account: workspaceConfig(
    'Account details are unavailable',
    'We could not finish rendering your account view.'
  ),
  chat: {
    title: 'Chat is temporarily unavailable',
    description: 'The conversation workspace crashed before it finished rendering.',
    actions: [
      { type: 'link', label: 'Go Home', href: '/', variant: 'primary' },
      { type: 'link', label: 'Open Help', href: '/help', variant: 'secondary' },
      { type: 'copyErrorId', label: 'Copy Error ID', variant: 'secondary' },
    ],
  },
  googleCallback: authConfig(
    'Sign-in callback failed',
    'We could not finish the Google sign-in handoff screen.'
  ),
  help: workspaceConfig(
    'Help is unavailable',
    'Support and documentation could not be rendered right now.'
  ),
  login: authConfig(
    'Sign-in is temporarily unavailable',
    'The authentication screen failed before you could continue.'
  ),
  register: authConfig(
    'Registration is temporarily unavailable',
    'The account creation screen failed before you could continue.'
  ),
  sandbox: workspaceConfig(
    'Sandbox is temporarily unavailable',
    'The sandbox view crashed before your experiment workspace loaded.'
  ),
  search: workspaceConfig(
    'Search is temporarily unavailable',
    'The search experience failed before results could be shown.'
  ),
  settings: workspaceConfig(
    'Settings are temporarily unavailable',
    'Your provider and model settings screen failed while rendering.'
  ),
  startup: generalConfig(
    'Startup could not finish',
    'Goblin Assistant hit a render failure during startup.'
  ),
  notFound: generalConfig(
    'This page could not be shown',
    'The not-found view failed while rendering the recovery page.'
  ),
  adminIndex: adminConfig(
    'Admin dashboard is unavailable',
    'The dashboard view crashed before admin telemetry could load.'
  ),
  adminLogs: adminConfig(
    'Admin logs are unavailable',
    'The logs view crashed before diagnostic data could render.'
  ),
  adminProviders: adminConfig(
    'Admin providers are unavailable',
    'The provider management view failed while rendering.'
  ),
  adminSettings: adminConfig(
    'Admin settings are unavailable',
    'The admin settings view failed while rendering.'
  ),
};

const getActionClassName = (variant: RouteBoundaryAction['variant']) =>
  variant === 'primary' ? primaryButtonClass : secondaryButtonClass;

export const formatBoundaryTechnicalDetail = (error: Error): string => {
  if (env.isDevelopment) {
    return [error.message, error.stack].filter(Boolean).join('\n\n');
  }

  return error.message;
};

export function RouteBoundaryFallback({
  title,
  description,
  actions,
  errorId,
  technicalDetail,
}: RouteBoundaryFallbackProps) {
  const [copiedErrorId, setCopiedErrorId] = useState(false);

  const visibleActions = actions.filter(action => action.type !== 'copyErrorId' || Boolean(errorId));

  const handleCopyErrorId = async () => {
    if (!errorId || !navigator.clipboard?.writeText) {
      return;
    }

    try {
      await navigator.clipboard.writeText(errorId);
      setCopiedErrorId(true);
    } catch {
      setCopiedErrorId(false);
    }
  };

  const handleReload = () => {
    window.location.reload();
  };

  return (
    <div className="min-h-screen bg-bg px-4 py-12">
      <div className="mx-auto flex min-h-[60vh] max-w-2xl items-center justify-center">
        <div className="w-full rounded-2xl border border-border bg-surface p-6 shadow-card">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-danger/15">
            <svg
              className="h-6 w-6 text-danger"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>

          <h1 className="text-2xl font-semibold text-text">{title}</h1>
          <p className="mt-2 text-sm text-muted">{description}</p>

          {errorId && (
            <p className="mt-4 text-xs text-muted" data-testid="route-boundary-error-id">
              Reference ID: <code className="rounded bg-bg px-2 py-1 text-text">{errorId}</code>
            </p>
          )}

          {(technicalDetail || errorId) && (
            <details className="mt-4 rounded-xl border border-border bg-bg p-4 text-sm">
              <summary className="cursor-pointer font-medium text-text">Technical details</summary>
              <div className="mt-3 space-y-3 text-xs text-muted">
                {errorId && (
                  <p>
                    Sentry event ID: <span className="font-mono text-text">{errorId}</span>
                  </p>
                )}
                {technicalDetail && (
                  <pre className="overflow-auto whitespace-pre-wrap break-words text-text">
                    {technicalDetail}
                  </pre>
                )}
              </div>
            </details>
          )}

          <div className="mt-6 flex flex-wrap gap-3">
            {visibleActions.map(action => {
              if (action.type === 'link') {
                return (
                  <a
                    key={`${action.type}-${action.label}-${action.href}`}
                    className={getActionClassName(action.variant)}
                    href={action.href}
                  >
                    {action.label}
                  </a>
                );
              }

              if (action.type === 'reload') {
                return (
                  <button
                    key={`${action.type}-${action.label}`}
                    className={getActionClassName(action.variant)}
                    onClick={handleReload}
                    type="button"
                  >
                    {action.label}
                  </button>
                );
              }

              return (
                <button
                  key={`${action.type}-${action.label}`}
                  className={getActionClassName(action.variant)}
                  onClick={handleCopyErrorId}
                  type="button"
                >
                  {copiedErrorId ? 'Copied Error ID' : action.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export function withRouteErrorBoundary<P extends object>(
  WrappedComponent: ComponentType<P>,
  routeKey: RouteBoundaryKey
) {
  const config = routeBoundaryConfig[routeKey];

  const ComponentWithRouteBoundary = (props: P) => (
    <ErrorBoundary
      boundaryName={`route:${routeKey}`}
      fallbackRender={({ error, errorId }: ErrorBoundaryRenderProps) => (
        <RouteBoundaryFallback
          title={config.title}
          description={config.description}
          actions={config.actions}
          errorId={errorId}
          technicalDetail={formatBoundaryTechnicalDetail(error)}
        />
      )}
    >
      <WrappedComponent {...props} />
    </ErrorBoundary>
  );

  ComponentWithRouteBoundary.displayName = `withRouteErrorBoundary(${
    WrappedComponent.displayName || WrappedComponent.name || 'Component'
  })`;

  return ComponentWithRouteBoundary;
}
