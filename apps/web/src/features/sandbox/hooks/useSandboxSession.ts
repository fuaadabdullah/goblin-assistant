import { useCallback, useEffect, useState } from 'react';
import { fetchJobLogs, fetchSandboxJobs, runSandboxCode } from '../api';
import { toUiError } from '../../../lib/ui-error';
import type { SandboxJob } from '../types';
import { devError } from '@/utils/dev-log';

export interface SandboxSessionState {
  jobs: SandboxJob[];
  jobsError: string | null;
  selectedJob: SandboxJob | null;
  code: string;
  language: string;
  logs: string;
  loading: boolean;
  setCode: (value: string) => void;
  setLanguage: (value: string) => void;
  refreshJobs: () => Promise<void>;
  runCode: () => Promise<void>;
  selectJob: (job: SandboxJob) => Promise<void>;
  clearCode: () => void;
}

interface SandboxSessionOptions {
  isGuest?: boolean;
  sandboxState?: 'loading' | 'enabled' | 'disabled';
}

export const useSandboxSession = ({
  isGuest = false,
  sandboxState = 'enabled',
}: SandboxSessionOptions = {}): SandboxSessionState => {
  const [jobs, setJobs] = useState<SandboxJob[]>([]);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<SandboxJob | null>(null);
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [logs, setLogs] = useState('');
  const [loading, setLoading] = useState(false);
  const sandboxUnavailable = sandboxState !== 'enabled';

  const refreshJobs = useCallback(async () => {
    if (isGuest) {
      setJobs([]);
      return;
    }
    if (sandboxUnavailable) {
      setJobs([]);
      setJobsError(
        sandboxState === 'loading'
          ? 'Checking sandbox availability...'
          : 'Sandbox service is currently disabled.'
      );
      return;
    }
    try {
      const jobsData = await fetchSandboxJobs();
      setJobsError(null);
      setJobs(jobsData);
    } catch (error) {
      const uiError = toUiError(error, {
        code: 'SANDBOX_JOBS_FAILED',
        userMessage: 'We could not load sandbox jobs right now.',
      });
      setJobsError(uiError.userMessage);
      devError('Failed to load sandbox jobs:', uiError);
    }
  }, [isGuest, sandboxState, sandboxUnavailable]);

  useEffect(() => {
    if (isGuest) {
      return;
    }
    if (sandboxUnavailable) {
      setJobs([]);
      setJobsError(
        sandboxState === 'loading'
          ? 'Checking sandbox availability...'
          : 'Sandbox service is currently disabled.'
      );
      return;
    }
    if (!isGuest) {
      refreshJobs();
    }
  }, [isGuest, refreshJobs, sandboxState, sandboxUnavailable]);

  const runCode = useCallback(async () => {
    if (!code) return;
    if (sandboxUnavailable) {
      setLogs('Sandbox service is currently disabled.');
      return;
    }
    setLoading(true);
    try {
      const output = await runSandboxCode({ code, language });
      setLogs(output);
      await refreshJobs();
    } catch (error) {
      const uiError = toUiError(error, {
        code: 'SANDBOX_RUN_FAILED',
        userMessage: 'We could not run that code right now.',
      });
      setLogs(uiError.userMessage);
    } finally {
      setLoading(false);
    }
  }, [code, language, refreshJobs, sandboxUnavailable]);

  const selectJob = useCallback(
    async (job: SandboxJob) => {
      if (isGuest) {
        setLogs('Sign in to view saved runs and logs.');
        return;
      }
      if (sandboxUnavailable) {
        setLogs('Sandbox service is currently disabled.');
        return;
      }
      setSelectedJob(job);
      try {
        const logData = await fetchJobLogs(job.id);
        setLogs(JSON.stringify(logData, null, 2));
      } catch (error) {
        const uiError = toUiError(error, {
          code: 'SANDBOX_LOGS_FAILED',
          userMessage: 'We could not load logs for that job.',
        });
        setLogs(uiError.userMessage);
      }
    },
    [isGuest, sandboxUnavailable]
  );

  const clearCode = useCallback(() => {
    setCode('');
  }, []);

  return {
    jobs,
    jobsError,
    selectedJob,
    code,
    language,
    logs,
    loading,
    setCode,
    setLanguage,
    refreshJobs,
    runCode,
    selectJob,
    clearCode,
  };
};
