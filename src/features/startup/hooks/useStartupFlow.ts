import { useEffect, useRef, useState } from 'react';
import { apiClient } from '../../../api/apiClient';
import { getRuntimeClient } from '../../../services/provider-router';
import { storeStartupDiagnostics } from '../../../utils/startup-diagnostics';
import { getEnabledModules } from '../../../config/features';
import { preloadRecentChat } from '../../../lib/chat-history';
import { trackPerformance } from '../../../utils/error-tracking';
import { useAuthStore } from '../../../store/authStore';
import type { StartupDiagnostics, StartupState, StartupStatus } from '../types';

const STATUS_MESSAGES: Record<StartupStatus, string> = {
  'checking-auth': 'Checking your session...',
  'loading-config': 'Loading configuration...',
  'initializing-runtime': 'Warming up the runtime...',
  ready: 'All systems ready.',
  error: 'Something went wrong while booting.',
};

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
const now = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());

export const resolveStartupDestinationRoute = (input: {
  isAuthenticated: boolean;
  isAdmin: boolean;
  isAdminModuleEnabled: boolean;
}): string => {
  if (!input.isAuthenticated) return '/';
  if (input.isAdmin && input.isAdminModuleEnabled) return '/admin';
  return '/chat';
};

export const useStartupFlow = (): StartupState => {
  const bootstrapFromSession = useAuthStore(state => state.bootstrapFromSession);
  const currentStatusRef = useRef<StartupStatus>('checking-auth');
  const [state, setState] = useState<StartupState>({
    status: 'checking-auth',
    message: STATUS_MESSAGES['checking-auth'],
  });
  const hasRunRef = useRef(false);

  useEffect(() => {
    if (hasRunRef.current) return;
    hasRunRef.current = true;
    let cancelled = false;
    let finished = false;
    const timings: {
      authMs?: number;
      configMs?: number;
      runtimeMs?: number;
      totalMs?: number;
    } = {};
    const bootStart = now();

    const setStep = (status: StartupStatus, message?: string, extras?: Partial<StartupState>) => {
      currentStatusRef.current = status;
      setState(prev => ({
        ...prev,
        status,
        message: message ?? STATUS_MESSAGES[status] ?? STATUS_MESSAGES.error,
        ...extras,
      }));
    };

    const fail = (message?: string) => {
      if (finished || cancelled) return;
      finished = true;
      window.clearTimeout(watchdog);
      timings.totalMs = Math.round(now() - bootStart);
      if (typeof timings.authMs === 'number') {
        trackPerformance('startup_auth_ms', timings.authMs, { outcome: 'error' });
      }
      if (typeof timings.configMs === 'number') {
        trackPerformance('startup_config_ms', timings.configMs, { outcome: 'error' });
      }
      if (typeof timings.runtimeMs === 'number') {
        trackPerformance('startup_runtime_ms', timings.runtimeMs, { outcome: 'error' });
      }
      if (typeof timings.totalMs === 'number') {
        trackPerformance('startup_total_ms', timings.totalMs, { outcome: 'error' });
      }
      const logId =
        typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
          ? crypto.randomUUID()
          : `boot-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
      const diagnostics: StartupDiagnostics = {
        logId,
        status: currentStatusRef.current,
        message: message ?? STATUS_MESSAGES.error,
        timestamp: new Date().toISOString(),
        authMs: timings.authMs,
        configMs: timings.configMs,
        runtimeMs: timings.runtimeMs,
        totalMs: timings.totalMs,
      };
      storeStartupDiagnostics(diagnostics);
      setState({
        status: 'error',
        message: message ?? STATUS_MESSAGES.error,
        destinationRoute: `/help?reason=startup_failed&logId=${encodeURIComponent(logId)}`,
        logId,
        diagnostics,
      });
    };

    const watchdog = window.setTimeout(() => {
      fail('Startup is taking longer than expected.');
    }, 12000);

    const run = async () => {
      try {
        setStep('checking-auth');
        const authStart = now();
        await bootstrapFromSession();
        timings.authMs = Math.round(now() - authStart);
        trackPerformance('startup_auth_ms', timings.authMs);
        if (cancelled) return;

        setStep('loading-config');
        const configStart = now();
        await Promise.race([apiClient.getRoutingInfo().catch(() => null), delay(900)]);
        timings.configMs = Math.round(now() - configStart);
        trackPerformance('startup_config_ms', timings.configMs);
        if (cancelled) return;
        const modules = getEnabledModules();
        setStep('loading-config', STATUS_MESSAGES['loading-config'], { modules });
        preloadRecentChat(5);

        setStep('initializing-runtime');
        const runtimeStart = now();
        const runtime = getRuntimeClient();
        await Promise.race([runtime.getProviders().catch(() => null), delay(900)]);
        timings.runtimeMs = Math.round(now() - runtimeStart);
        trackPerformance('startup_runtime_ms', timings.runtimeMs);
        if (cancelled) return;

        const authState = useAuthStore.getState();
        const destinationRoute = resolveStartupDestinationRoute({
          isAuthenticated: authState.isAuthenticated,
          isAdmin: authState.hasRole('admin'),
          isAdminModuleEnabled: modules.admin,
        });

        finished = true;
        window.clearTimeout(watchdog);
        timings.totalMs = Math.round(now() - bootStart);
        trackPerformance('startup_total_ms', timings.totalMs);
        setState(prev => ({
          ...prev,
          status: 'ready',
          message: STATUS_MESSAGES.ready,
          destinationRoute,
        }));
      } catch (error) {
        if (cancelled) return;
        fail('We hit a snag while booting. Redirecting to help.');
      }
    };

    run();
    return () => {
      cancelled = true;
      window.clearTimeout(watchdog);
    };
  }, [bootstrapFromSession]);

  return state;
};
