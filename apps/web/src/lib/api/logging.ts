import { getBackend } from './shared';

export const loggingMethods = {
  async getRaptorLogs(limit = 100) {
    return getBackend(`/logs?limit=${limit}`);
  },
};
