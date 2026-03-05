/**
 * Datadog Real User Monitoring (RUM) and Browser Logs wiring.
 *
 * Client-only and optional: if Datadog isn't available or init fails, helpers are no-ops.
 */

import type { LogsInitConfiguration } from '@datadog/browser-logs';
import type { RumInitConfiguration } from '@datadog/browser-rum';

type DatadogRumApi = typeof import('@datadog/browser-rum').datadogRum;
type DatadogLogsApi = typeof import('@datadog/browser-logs').datadogLogs;

let datadogRum: DatadogRumApi | null = null;
let datadogLogs: DatadogLogsApi | null = null;
let isInitialized = false;

export async function initDatadog(): Promise<void> {
  if (isInitialized) return;

  try {
    const [rumModule, logsModule] = await Promise.all([
      import('@datadog/browser-rum'),
      import('@datadog/browser-logs'),
    ]);

    datadogRum = rumModule.datadogRum;
    datadogLogs = logsModule.datadogLogs;

    const rumConfig: RumInitConfiguration = {
      applicationId: process.env.NEXT_PUBLIC_DD_APPLICATION_ID || 'goblin-assistant',
      clientToken: process.env.NEXT_PUBLIC_DD_CLIENT_TOKEN || 'placeholder-token',
      site: 'datadoghq.com',
      service: 'goblin-assistant-frontend',
      env: process.env.NEXT_PUBLIC_DD_ENV || 'development',
      version: process.env.NEXT_PUBLIC_DD_VERSION || '1.0.0',
      sessionSampleRate: 100,
      sessionReplaySampleRate: 20,
      trackUserInteractions: true,
      trackResources: true,
      trackLongTasks: true,
      defaultPrivacyLevel: 'mask-user-input',
    };

    datadogRum.init(rumConfig);

    // Datadog's `LogsInitConfiguration` should inherit `clientToken` from the core init config,
    // but TS (with our module resolution settings) can fail excess-property checks here.
    // Runtime config is correct; we cast to keep this wiring simple.
    const logsConfig = {
      clientToken: rumConfig.clientToken,
      site: rumConfig.site,
      service: rumConfig.service,
      env: rumConfig.env,
      version: rumConfig.version,
      forwardErrorsToLogs: true,
      sessionSampleRate: 100,
    } as unknown as LogsInitConfiguration;

    datadogLogs.init(logsConfig);
    datadogRum.startSessionReplayRecording();

    isInitialized = true;
  } catch (error) {
    // Keep everything as no-ops.
    console.warn('Failed to initialize Datadog:', error);
    datadogRum = null;
    datadogLogs = null;
  }
}

export function getDatadogRum(): DatadogRumApi | null {
  return datadogRum;
}

export function getDatadogLogs(): DatadogLogsApi | null {
  return datadogLogs;
}

export const logEvent = (message: string, context?: Record<string, unknown>) => {
  datadogLogs?.logger?.info(message, context);
};

export const logError = (error: Error, context?: Record<string, unknown>) => {
  datadogLogs?.logger?.error(error.message, {
    ...context,
    stack: error.stack,
    name: error.name,
  });
};

export const logWarning = (message: string, context?: Record<string, unknown>) => {
  datadogLogs?.logger?.warn(message, context);
};

export const trackLLMCall = (provider: string, model: string, tokens?: number, cost?: number) => {
  datadogRum?.addAction('llm_call', { provider, model, tokens, cost });
};

export const trackRoutingDecision = (fromProvider: string, toProvider: string, reason: string) => {
  datadogRum?.addAction('routing_decision', {
    from_provider: fromProvider,
    to_provider: toProvider,
    reason,
  });
};
