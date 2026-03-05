import { apiClient } from '../../../api/apiClient';
import { UiError } from '../../../lib/ui-error';
import type { SandboxJob } from '../types';

interface SandboxJobsResponse {
  jobs: Array<{
    job_id?: string;
    id?: string;
    status?: string;
    task?: string;
    created_at?: number | string;
    language?: string;
  }>;
}

const createFallbackId = () => `job_${Math.random().toString(16).slice(2, 8)}`;

const normalizeJob = (job: SandboxJobsResponse['jobs'][number]): SandboxJob => {
  const created =
    typeof job.created_at === 'number'
      ? new Date(job.created_at * 1000).toISOString()
      : job.created_at || new Date().toISOString();
  return {
    id: job.id || job.job_id || createFallbackId(),
    status: (job.status as SandboxJob['status']) || 'pending',
    created_at: created,
    code_snippet: job.task,
    language: job.language,
  };
};

export const fetchSandboxJobs = async (): Promise<SandboxJob[]> => {
  try {
    const jobsData = await apiClient.getSandboxJobs();
    if (Array.isArray(jobsData)) {
      return jobsData.map(job => normalizeJob(job as SandboxJobsResponse['jobs'][number]));
    }
    const response = jobsData as SandboxJobsResponse;
    return (response.jobs || []).map(normalizeJob);
  } catch (error) {
    throw new UiError(
      {
        code: 'SANDBOX_JOBS_FAILED',
        userMessage: 'We could not load sandbox jobs right now.',
      },
      error
    );
  }
};

export const fetchJobLogs = async (jobId: string): Promise<unknown> => {
  try {
    return await apiClient.getJobLogs(jobId);
  } catch (error) {
    throw new UiError(
      {
        code: 'SANDBOX_LOGS_FAILED',
        userMessage: 'We could not load logs for that job.',
      },
      error
    );
  }
};

export const runSandboxCode = async (payload: {
  code: string;
  language: string;
}): Promise<string> => {
  try {
    const response = await apiClient.runSandboxCode(payload);
    return response.output;
  } catch (error) {
    throw new UiError(
      {
        code: 'SANDBOX_RUN_FAILED',
        userMessage: 'We could not run that code right now.',
      },
      error
    );
  }
};
