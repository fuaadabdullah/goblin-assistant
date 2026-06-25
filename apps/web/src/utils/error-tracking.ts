/**
 * Enhanced error tracking and logging utilities for Goblin Assistant
 * Integrates with Sentry for comprehensive monitoring
 */

import { logErrorToService } from './monitoring';
import { devWarn } from './dev-log';

// Lightweight logging helpers (replace former Datadog calls)
const logEvent = (message: string, context?: Record<string, unknown>) => {
  if (process.env['NODE_ENV'] === 'development') {
    devWarn(`[event] ${message}`, context);
  }
};

const logError = (error: Error, context?: Record<string, unknown>) => {
  logErrorToService(error, context);
};

const trackLLMCall = (provider: string, model: string, tokens?: number, cost?: number) => {
  logEvent('llm_call', { provider, model, tokens, cost });
};

const trackRoutingDecision = (fromProvider: string, toProvider: string, reason: string) => {
  logEvent('routing_decision', { from_provider: fromProvider, to_provider: toProvider, reason });
};

const nowIso = () => new Date().toISOString();

const getRuntimeMetadata = () => ({
  userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'server',
  url: typeof window !== 'undefined' ? window.location.href : 'server',
});

const buildOperationLogContext = <TContext extends Record<string, unknown>>(
  context: TContext,
  duration: number,
  success: boolean
) => ({
  ...context,
  duration,
  success,
  timestamp: nowIso(),
});

const buildErrorPayload = (error: unknown) => ({
  name: error instanceof Error ? error.name : 'Unknown',
  message: error instanceof Error ? error.message : String(error),
  stack: error instanceof Error ? error.stack : undefined,
});

const normalizeError = (error: unknown) => (error instanceof Error ? error : new Error(String(error)));

const rethrowOperationError = (error: unknown, operation: string): never => {
  if (error instanceof Error) {
    throw error;
  }

  throw new Error(`Operation failed: ${operation} - ${String(error)}`);
};

const createGlobalErrorListener =
  (type: 'unhandledrejection' | 'uncaughterror') =>
  (event: PromiseRejectionEvent | ErrorEvent) => {
    if (type === 'unhandledrejection') {
      const rejectionEvent = event as PromiseRejectionEvent;
      const error = new Error(`Unhandled promise rejection: ${rejectionEvent.reason}`);

      logError(error, {
        type,
        reason: rejectionEvent.reason,
        timestamp: nowIso(),
        ...getRuntimeMetadata(),
      });
      logErrorToService(error, {
        type,
        reason: rejectionEvent.reason,
      });
      return;
    }

    const errorEvent = event as ErrorEvent;
    const error = errorEvent.error || new Error(errorEvent.message);

    logError(error, {
      type,
      filename: errorEvent.filename,
      lineno: errorEvent.lineno,
      colno: errorEvent.colno,
      timestamp: nowIso(),
      ...getRuntimeMetadata(),
    });
    logErrorToService(error, {
      type,
      filename: errorEvent.filename,
      lineno: errorEvent.lineno,
      colno: errorEvent.colno,
    });
  };

const handleVisibilityChange = () => {
  logEvent('Page visibility changed', {
    hidden: document.hidden,
    timestamp: nowIso(),
  });
};

// Custom error types for better categorization
export class APIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public endpoint?: string,
    public method?: string,
    public context?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export class NetworkError extends Error {
  constructor(
    message: string,
    public endpoint?: string,
    public originalError?: Error
  ) {
    super(message);
    this.name = 'NetworkError';
  }
}

export class ValidationError extends Error {
  constructor(
    message: string,
    public field?: string,
    public value?: unknown
  ) {
    super(message);
    this.name = 'ValidationError';
  }
}

// Enhanced error tracking wrapper
export const withErrorTracking = async <T>(
  operation: () => Promise<T>,
  context: {
    operation: string;
    endpoint?: string | undefined;
    method?: string | undefined;
    userId?: string | undefined;
    additionalContext?: Record<string, unknown> | undefined;
  }
): Promise<T> => {
  const startTime = Date.now();

  try {
    const result = await operation();
    const duration = Date.now() - startTime;

    logEvent(`API call completed: ${context.operation}`, buildOperationLogContext(context, duration, true));

    return result;
  } catch (error) {
    const duration = Date.now() - startTime;

    logError(normalizeError(error), {
      ...buildOperationLogContext(context, duration, false),
      ...getRuntimeMetadata(),
      error: buildErrorPayload(error),
    });

    return rethrowOperationError(error, context.operation);
  }
};

// API call wrapper with automatic error tracking
export const trackApiCall = async <T>(
  apiCall: () => Promise<T>,
  endpoint: string,
  method: string = 'GET',
  additionalContext?: Record<string, unknown>
): Promise<T> => {
  return withErrorTracking(apiCall, {
    operation: `API ${method} ${endpoint}`,
    endpoint,
    method,
    additionalContext,
  });
};

// LLM call tracking wrapper
export const trackLLMOperation = async <T>(
  operation: () => Promise<T>,
  context: {
    provider: string;
    model: string;
    operation: string;
    inputTokens?: number;
    outputTokens?: number;
    cost?: number;
  }
): Promise<T> => {
  const startTime = Date.now();

  try {
    const result = await operation();
    const duration = Date.now() - startTime;

    // Track successful LLM call
    trackLLMCall(context.provider, context.model, context.outputTokens, context.cost);

    logEvent(`LLM operation completed: ${context.operation}`, {
      ...context,
      duration,
      success: true,
      timestamp: nowIso(),
    });

    return result;
  } catch (error) {
    const duration = Date.now() - startTime;

    logError(error instanceof Error ? error : new Error(String(error)), {
      ...context,
      duration,
      success: false,
      timestamp: nowIso(),
    });

    throw error;
  }
};

// Routing decision tracking
export const trackRoutingOperation = (
  fromProvider: string,
  toProvider: string,
  reason: string,
  context?: Record<string, unknown>
) => {
  trackRoutingDecision(fromProvider, toProvider, reason);

  logEvent('Routing decision made', {
    fromProvider,
    toProvider,
    reason,
    ...context,
    timestamp: nowIso(),
  });
};

// User interaction tracking
export const trackUserAction = (action: string, context?: Record<string, unknown>) => {
  logEvent(`User action: ${action}`, {
    ...context,
    timestamp: nowIso(),
    ...getRuntimeMetadata(),
  });
};

// Performance monitoring
export const trackPerformance = (
  metric: string,
  value: number,
  context?: Record<string, unknown>
) => {
  logEvent(`Performance metric: ${metric}`, {
    value,
    ...context,
    timestamp: nowIso(),
  });
};

// Error boundary helper for React components
export const logComponentError = (
  error: Error,
  errorInfo: { componentStack: string },
  componentName: string,
  additionalContext?: Record<string, unknown>
) => {
  // Log to Datadog
  logError(error, {
    component: componentName,
    componentStack: errorInfo.componentStack,
    ...additionalContext,
    timestamp: nowIso(),
    ...getRuntimeMetadata(),
  });

  // Log to Sentry
  logErrorToService(error, {
    component: componentName,
    componentStack: errorInfo.componentStack,
    ...additionalContext,
  });
};

// Global error handler for unhandled errors
export const setupGlobalErrorTracking = () => {
  // Skip setup on server-side
  if (typeof window === 'undefined') return;

  window.addEventListener('unhandledrejection', createGlobalErrorListener('unhandledrejection'));
  window.addEventListener('error', createGlobalErrorListener('uncaughterror'));
  document.addEventListener('visibilitychange', handleVisibilityChange);
};

// Network status monitoring
export const monitorNetworkStatus = () => {
  // Skip setup on server-side
  if (typeof window === 'undefined') return;

  const logNetworkStatus = (online: boolean) => {
    logEvent(`Network status changed: ${online ? 'online' : 'offline'}`, {
      online,
      timestamp: nowIso(),
      userAgent: navigator.userAgent,
    });
  };

  window.addEventListener('online', () => logNetworkStatus(true));
  window.addEventListener('offline', () => logNetworkStatus(false));

  // Log initial status
  logNetworkStatus(navigator.onLine);
};

// Export all utilities
export default {
  withErrorTracking,
  trackApiCall,
  trackLLMOperation,
  trackRoutingOperation,
  trackUserAction,
  trackPerformance,
  logComponentError,
  setupGlobalErrorTracking,
  monitorNetworkStatus,
  APIError,
  NetworkError,
  ValidationError,
};
