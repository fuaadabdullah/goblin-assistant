import { getBackend, postBackend } from './shared';

export const sandboxMethods = {
  async getSandboxJobs() {
    return getBackend('/sandbox/jobs');
  },

  async getJobLogs(jobId: string) {
    return getBackend(`/sandbox/jobs/${jobId}/logs`);
  },

  async runSandboxCode(payload: { code: string; language?: string; timeout?: number }) {
    return postBackend('/sandbox/run', payload);
  },
};
