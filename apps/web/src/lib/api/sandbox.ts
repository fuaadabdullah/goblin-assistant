import { getFrontend, postFrontend } from './shared';

const INTERNAL_SANDBOX_PREFIX = '/api/sandbox';

export const sandboxMethods = {
  async getSandboxJobs() {
    return getFrontend(`${INTERNAL_SANDBOX_PREFIX}/jobs`);
  },

  async getJobLogs(jobId: string) {
    return getFrontend(`${INTERNAL_SANDBOX_PREFIX}/jobs/${jobId}/logs`);
  },

  async runSandboxCode(payload: {
    code?: string;
    source?: string;
    language?: string;
    timeout?: number;
  }) {
    return postFrontend(`${INTERNAL_SANDBOX_PREFIX}/run`, {
      source: payload.source ?? payload.code,
      language: payload.language,
      timeout: payload.timeout,
    });
  },
};
