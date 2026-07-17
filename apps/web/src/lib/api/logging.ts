import { getFrontend, postFrontend } from './shared';

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
    return getFrontend(`/api/raptor/logs?limit=${limit}`);
  },
  async submitErrorReport(payload: ErrorReportPayload) {
    return postFrontend('/api/errors', payload);
  },
};
