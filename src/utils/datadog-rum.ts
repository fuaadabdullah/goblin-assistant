/**
 * Datadog Real User Monitoring (RUM) and Browser Logs configuration
 * for the Goblin Assistant frontend.
 */

interface DatadogRum {
  init: (config: unknown) => void;
  startSessionReplayRecording: () => void;
  setUser: (user: unknown) => void;
  addAction: (name: string, attributes?: unknown) => void;
  addError: (error: unknown, context?: unknown) => void;
  setGlobalContext: (context: unknown) => void;
}

interface DatadogLogs {
  init: (config: unknown) => void;
  logger: {
    info: (message: string, context?: unknown) => void;
    error: (message: string, context?: unknown) => void;
    warn: (message: string, context?: unknown) => void;
  };
}

// Mock implementations when Datadog modules are not available
const mockDatadogRum: DatadogRum = {
  init: () => console.log('Datadog RUM not available'),
  startSessionReplayRecording: () => {},
  setUser: () => {},
  addAction: () => {},
  addError: () => {},
  setGlobalContext: () => {},
};

const mockDatadogLogs: DatadogLogs = {
  init: () => console.log('Datadog Logs not available'),
  logger: {
    info: () => {},
    error: () => {},
    warn: () => {},
  },
};

// Global variables to hold the actual Datadog instances
let datadogRum: DatadogRum = mockDatadogRum;
let datadogLogs: DatadogLogs = mockDatadogLogs;
let isInitialized = false;

/**
 * Initialize Datadog RUM and Browser Logs
 * This function should be called once at application startup
 */
export async function initDatadog(): Promise<void> {
  if (isInitialized) return;

  try {
    // Dynamically import Datadog modules
    const [rumModule, logsModule, reactModule] = await Promise.all([
      import('@datadog/browser-rum'),
      import('@datadog/browser-logs'),
      import('@datadog/browser-rum-react')
    ]);

    datadogRum = rumModule.datadogRum;
    datadogLogs = logsModule.datadogLogs;
    const reactPlugin = reactModule.reactPlugin;

    // Configuration from environment variables
    const config = {
      applicationId: import.meta.env.VITE_DD_APPLICATION_ID || 'goblin-assistant',
      clientToken: import.meta.env.VITE_DD_CLIENT_TOKEN || 'placeholder-token',
      site: 'datadoghq.com',
      service: 'goblin-assistant-frontend',
      env: import.meta.env.VITE_DD_ENV || 'development',
      version: import.meta.env.VITE_DD_VERSION || '1.0.0',
      sessionSampleRate: 100,
      sessionReplaySampleRate: 20,
      trackUserInteractions: true,
      trackResources: true,
      trackLongTasks: true,
      defaultPrivacyLevel: 'mask-user-input' as const,
      plugins: [reactPlugin({ router: true })],
    };

    // Initialize RUM
    datadogRum.init(config);

    // Initialize Browser Logs
    datadogLogs.init({
      clientToken: config.clientToken,
      site: config.site,
      service: config.service,
      env: config.env,
      version: config.version,
      forwardErrorsToLogs: true,
      sessionSampleRate: 100,
    });

    // Start session replay recording
    datadogRum.startSessionReplayRecording();

    isInitialized = true;
    console.log('Datadog RUM and Browser Logs initialized successfully');
  } catch (error) {
    console.warn('Failed to initialize Datadog:', error);
    // Keep using mock implementations
  }
}

/**
 * Get the Datadog RUM instance
 */
export function getDatadogRum(): DatadogRum {
  return datadogRum;
}

/**
 * Get the Datadog Logs instance
 */
export function getDatadogLogs(): DatadogLogs {
  return datadogLogs;
}

// Custom logging functions
export const logEvent = (message: string, context?: Record<string, unknown>) => {
  datadogLogs.logger.info(message, context);
};

export const logError = (error: Error, context?: Record<string, unknown>) => {
  datadogLogs.logger.error(error.message, {
    ...context,
    stack: error.stack,
    name: error.name,
  });
};

export const logWarning = (message: string, context?: Record<string, unknown>) => {
  datadogLogs.logger.warn(message, context);
};

// Performance tracking helpers
export const trackLLMCall = (provider: string, model: string, tokens?: number, cost?: number) => {
  datadogRum.addAction('llm_call', {
    provider,
    model,
    tokens,
    cost,
  });
};

export const trackRoutingDecision = (fromProvider: string, toProvider: string, reason: string) => {
  datadogRum.addAction('routing_decision', {
    from_provider: fromProvider,
    to_provider: toProvider,
    reason,
  });
};
