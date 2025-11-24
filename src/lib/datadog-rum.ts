/**
 * Datadog Real User Monitoring (RUM) and Browser Logs configuration
 * for the Goblin Assistant frontend.
 */

// Mock implementations when Datadog modules are not available
const mockDatadogRum = {
  init: () => console.log('Datadog RUM not available'),
  startSessionReplayRecording: () => {},
  setUser: () => {},
  addAction: () => {},
  addError: () => {},
};

const mockDatadogLogs = {
  init: () => console.log('Datadog Logs not available'),
  logger: {},
};

// Try to import Datadog modules, fall back to mocks if not available
let datadogRum: any = mockDatadogRum;
let datadogLogs: any = mockDatadogLogs;

try {
  // These imports will fail if modules are not installed
  const rumModule = require('@datadog/browser-rum');
  const logsModule = require('@datadog/browser-logs');
  datadogRum = rumModule.datadogRum;
  datadogLogs = logsModule.datadogLogs;
} catch (e) {
  // Modules not available, using mocks
}

// Configuration from environment variables
const config = {
  applicationId: process.env.NEXT_PUBLIC_DD_APPLICATION_ID || '',
  clientToken: process.env.NEXT_PUBLIC_DD_CLIENT_TOKEN || '',
  site: process.env.NEXT_PUBLIC_DD_SITE || 'datadoghq.com',
  service: process.env.NEXT_PUBLIC_DD_SERVICE || 'goblin-frontend',
  env: process.env.NEXT_PUBLIC_DD_ENV || 'dev',
  version: process.env.NEXT_PUBLIC_DD_VERSION || '1.0.0',
  sampleRate: parseFloat(process.env.NEXT_PUBLIC_DD_SAMPLE_RATE || '100'),
  trackInteractions: true,
  trackFrustrations: true,
  trackResources: true,
  trackLongTasks: true,
  defaultPrivacyLevel: 'mask-user-input' as const,
};

// Initialize RUM if we have the required configuration
export const initDatadogRUM = () => {
  if (!config.applicationId || !config.clientToken) {
    console.warn('Datadog RUM not initialized: missing applicationId or clientToken');
    return;
  }

  try {
    datadogRum.init({
      applicationId: config.applicationId,
      clientToken: config.clientToken,
      site: config.site,
      service: config.service,
      env: config.env,
      version: config.version,
      sampleRate: config.sampleRate,
      trackInteractions: config.trackInteractions,
      trackFrustrations: config.trackFrustrations,
      trackResources: config.trackResources,
      trackLongTasks: config.trackLongTasks,
      defaultPrivacyLevel: config.defaultPrivacyLevel,
      // Custom action name for routing
      beforeSend: (event: any) => {
        // Add custom context for routing decisions
        if (event.type === 'action' && event.action?.target?.name) {
          event.context = {
            ...event.context,
            routing: {
              target: event.action.target.name,
              timestamp: new Date().toISOString(),
            },
          };
        }
        return true;
      },
    });

    // Set user context if available
    const userId = localStorage.getItem('user_id');
    if (userId) {
      datadogRum.setUser({
        id: userId, // Hash this in production for privacy
        // Add other user properties as needed
      });
    }

    // Set global context
    datadogRum.setGlobalContext({
      app: 'goblin-assistant',
      platform: 'web',
      build_info: {
        version: config.version,
        env: config.env,
      },
    });

    console.log('Datadog RUM initialized successfully');
  } catch (error) {
    console.error('Failed to initialize Datadog RUM:', error);
  }
};

// Initialize Browser Logs
export const initDatadogLogs = () => {
  if (!config.clientToken) {
    console.warn('Datadog Logs not initialized: missing clientToken');
    return;
  }

  try {
    datadogLogs.init({
      clientToken: config.clientToken,
      site: config.site,
      service: config.service,
      env: config.env,
      version: config.version,
      forwardErrorsToLogs: true,
      sampleRate: config.sampleRate,
      // Forward console logs to Datadog
      forwardConsoleLogs: ['error', 'warn', 'info'],
      // Custom logger for application events
      beforeSend: (log: any) => {
        // Add context to logs
        log.context = {
          ...log.context,
          frontend: {
            userAgent: navigator.userAgent,
            url: window.location.href,
            timestamp: new Date().toISOString(),
          },
        };
        return true;
      },
    });

    console.log('Datadog Browser Logs initialized successfully');
  } catch (error) {
    console.error('Failed to initialize Datadog Browser Logs:', error);
  }
};

// Custom logging functions
export const logEvent = (message: string, context?: Record<string, any>) => {
  datadogLogs.logger.info(message, context);
};

export const logError = (error: Error, context?: Record<string, any>) => {
  datadogLogs.logger.error(error.message, {
    ...context,
    stack: error.stack,
    name: error.name,
  });
};

export const logWarning = (message: string, context?: Record<string, any>) => {
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

// Initialize both RUM and Logs
export const initDatadog = () => {
  initDatadogRUM();
  initDatadogLogs();
};

// Export for use in _app.tsx or main entry point
export default {
  initDatadog,
  initDatadogRUM,
  initDatadogLogs,
  logEvent,
  logError,
  logWarning,
  trackLLMCall,
  trackRoutingDecision,
};
