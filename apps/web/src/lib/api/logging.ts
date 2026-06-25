import { getBackend, postFrontend } from './shared';
import { V1_API_PREFIX } from './http-client';

export interface ErrorReportPayload {
  message: string;
  stack?: string | undefined;
  digest?: string | undefined;
  errorId?: string | undefined;
  timestamp: string;
  userAgent: string;
  url: string;
  context?: Record<string, unknown> | undefined;
}

export const loggingMethods = {
  async getRaptorLogs(limit = 100) {
    return getBackend(`${V1_API_PREFIX}/raptor/logs?limit=${limit}`);
  },
  async submitErrorReport(payload: ErrorReportPayload) {
    return postFrontend('/api/errors', payload);
  },
};
