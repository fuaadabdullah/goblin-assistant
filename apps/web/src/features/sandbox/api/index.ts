import { apiClient } from '@/lib/api';
import { UiError } from '../../../lib/ui-error';
import { getUserMessage } from '../../../lib/error/toast';
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

interface SandboxRunResponse {
  output: string;
  job_id?: string;
  logs?: string;
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
      return jobsData.map((job) => normalizeJob(job as SandboxJobsResponse['jobs'][number]));
    }
    const response = jobsData as SandboxJobsResponse;
    return (response.jobs || []).map(normalizeJob);
  } catch (error) {
    throw new UiError(
      {
        code: 'SANDBOX_JOBS_FAILED',
        userMessage: getUserMessage(error),
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
        userMessage: getUserMessage(error),
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
    const response = (await apiClient.runSandboxCode(payload)) as SandboxRunResponse;
    if (typeof response === 'string') {
      return response;
    }
    if (response.output) {
      return response.output;
    }
    if (response.job_id) {
      try {
        const jobLogs = await apiClient.getJobLogs(response.job_id);
        if (typeof jobLogs === 'string') {
          return jobLogs;
        }
        if (jobLogs && typeof jobLogs === 'object' && 'logs' in jobLogs) {
          return String((jobLogs as { logs?: string }).logs ?? '');
        }
      } catch {
        // Fall through to a queued-message fallback below.
      }
      return `Job queued: ${response.job_id}`;
    }
    return response.logs || '';
  } catch (error) {
    throw new UiError(
      {
        code: 'SANDBOX_RUN_FAILED',
        userMessage: getUserMessage(error),
      },
      error
    );
  }
};
