import { getBackend } from './shared';
import { V1_API_PREFIX } from './http-client';

export const loggingMethods = {
  async getRaptorLogs(limit = 100) {
    return getBackend(`${V1_API_PREFIX}/raptor/logs?limit=${limit}`);
  },
};
