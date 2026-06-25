import { V1_API_PREFIX, getBackend, postBackend } from './shared';

export const sandboxMethods = {
  async getSandboxJobs() {
    return getBackend(`${V1_API_PREFIX}/sandbox/jobs`);
  },

  async getJobLogs(jobId: string) {
    return getBackend(`${V1_API_PREFIX}/sandbox/jobs/${jobId}/logs`);
  },

  async runSandboxCode(payload: {
    code?: string;
    source?: string;
    language?: string;
    timeout?: number;
  }) {
    return postBackend(`${V1_API_PREFIX}/sandbox/run`, {
      source: payload.source ?? payload.code,
      language: payload.language,
      timeout: payload.timeout,
    });
  },
};
