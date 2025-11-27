/**
 * Enhanced error tracking and logging utilities for Goblin Assistant
 * Integrates with Datadog RUM and Browser Logs for comprehensive monitoring
 */

import { logError, logWarning, logEvent, trackLLMCall, trackRoutingDecision } from './datadog-rum';

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
    endpoint?: string;
    method?: string;
    userId?: string;
    additionalContext?: Record<string, unknown>;
  }
): Promise<T> => {
  const startTime = Date.now();

  try {
    const result = await operation();
    const duration = Date.now() - startTime;

    // Log successful operations for performance monitoring
    logEvent(`API call completed: ${context.operation}`, {
      ...context,
      duration,
      success: true,
      timestamp: new Date().toISOString(),
    });

    return result;
  } catch (error) {
    const duration = Date.now() - startTime;

    // Enhanced error logging with context
    const errorContext = {
      ...context,
      duration,
      success: false,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
      error: {
        name: error instanceof Error ? error.name : 'Unknown',
        message: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
      },
    };

    // Log to Datadog
    logError(error instanceof Error ? error : new Error(String(error)), errorContext);

    // Re-throw with enhanced context
    if (error instanceof Error) {
      throw error;
    } else {
      throw new Error(`Operation failed: ${context.operation} - ${String(error)}`);
    }
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
      timestamp: new Date().toISOString(),
    });

    return result;
  } catch (error) {
    const duration = Date.now() - startTime;

    logError(error instanceof Error ? error : new Error(String(error)), {
      ...context,
      duration,
      success: false,
      timestamp: new Date().toISOString(),
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
    timestamp: new Date().toISOString(),
  });
};

// User interaction tracking
export const trackUserAction = (
  action: string,
  context?: Record<string, unknown>
) => {
  logEvent(`User action: ${action}`, {
    ...context,
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    url: window.location.href,
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
    timestamp: new Date().toISOString(),
  });
};

// Error boundary helper for React components
export const logComponentError = (
  error: Error,
  errorInfo: { componentStack: string },
  componentName: string,
  additionalContext?: Record<string, unknown>
) => {
  logError(error, {
    component: componentName,
    componentStack: errorInfo.componentStack,
    ...additionalContext,
    timestamp: new Date().toISOString(),
    userAgent: navigator.userAgent,
    url: window.location.href,
  });
};

// Global error handler for unhandled errors
export const setupGlobalErrorTracking = () => {
  // Handle unhandled promise rejections
  window.addEventListener('unhandledrejection', (event) => {
    logError(new Error(`Unhandled promise rejection: ${event.reason}`), {
      type: 'unhandledrejection',
      reason: event.reason,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    });
  });

  // Handle uncaught errors
  window.addEventListener('error', (event) => {
    logError(event.error || new Error(event.message), {
      type: 'uncaughterror',
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href,
    });
  });

  // Log page visibility changes (useful for performance monitoring)
  document.addEventListener('visibilitychange', () => {
    logEvent('Page visibility changed', {
      hidden: document.hidden,
      timestamp: new Date().toISOString(),
    });
  });
};

// Network status monitoring
export const monitorNetworkStatus = () => {
  const logNetworkStatus = (online: boolean) => {
    logEvent(`Network status changed: ${online ? 'online' : 'offline'}`, {
      online,
      timestamp: new Date().toISOString(),
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
