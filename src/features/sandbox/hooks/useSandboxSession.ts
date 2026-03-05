import { useCallback, useEffect, useState } from 'react';
import { fetchJobLogs, fetchSandboxJobs, runSandboxCode } from '../api';
import { toUiError } from '../../../lib/ui-error';
import type { SandboxJob } from '../types';

export interface SandboxSessionState {
  jobs: SandboxJob[];
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
}

export const useSandboxSession = ({ isGuest = false }: SandboxSessionOptions = {}): SandboxSessionState => {
  const [jobs, setJobs] = useState<SandboxJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<SandboxJob | null>(null);
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [logs, setLogs] = useState('');
  const [loading, setLoading] = useState(false);

  const refreshJobs = useCallback(async () => {
    if (isGuest) {
      setJobs([]);
      return;
    }
    try {
      const jobsData = await fetchSandboxJobs();
      setJobs(jobsData);
    } catch (error) {
      const uiError = toUiError(error, {
        code: 'SANDBOX_JOBS_FAILED',
        userMessage: 'Unable to load sandbox jobs.',
      });
      console.error('Failed to load sandbox jobs:', uiError);
    }
  }, [isGuest]);

  useEffect(() => {
    if (!isGuest) {
      refreshJobs();
    }
  }, [isGuest, refreshJobs]);

  const runCode = useCallback(async () => {
    if (!code) return;
    setLoading(true);
    try {
      const output = await runSandboxCode({ code, language });
      setLogs(output);
      await refreshJobs();
    } catch (error) {
      const uiError = toUiError(error, {
        code: 'SANDBOX_RUN_FAILED',
        userMessage: 'Unable to run that code right now.',
      });
      setLogs(uiError.userMessage);
    } finally {
      setLoading(false);
    }
  }, [code, language, refreshJobs]);

  const selectJob = useCallback(async (job: SandboxJob) => {
    if (isGuest) {
      setLogs('Sign in to view saved runs and logs.');
      return;
    }
    setSelectedJob(job);
    try {
      const logData = await fetchJobLogs(job.id);
      setLogs(JSON.stringify(logData, null, 2));
    } catch (error) {
      const uiError = toUiError(error, {
        code: 'SANDBOX_LOGS_FAILED',
        userMessage: 'Unable to load logs for that job.',
      });
      setLogs(uiError.userMessage);
    }
  }, [isGuest]);

  const clearCode = useCallback(() => {
    setCode('');
  }, []);

  return {
    jobs,
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
