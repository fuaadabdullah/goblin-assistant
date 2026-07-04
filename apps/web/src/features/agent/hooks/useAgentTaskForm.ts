import type { FormEvent } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { getAgentTask, getAgentTaskEvents, submitAgentTask } from '../api';
import { toUiError } from '../../../lib/ui-error';
import { getUserMessage } from '../../../lib/error/toast';
import { useToast } from '../../../hooks/useToast';
import type { AgentTaskRecord } from '@/lib/api/api-types';

export interface AgentTaskFormState {
  task: string;
  repoUrl: string;
  baseBranch: string;
  branchName: string;
  testsCommand: string;
  issueUrl: string;
  issueNumber: string;
  issueTitle: string;
  issueBody: string;
  submitting: boolean;
  refreshing: boolean;
  activeTask: AgentTaskRecord | null;
  error: string | null;
  setTask: (value: string) => void;
  setRepoUrl: (value: string) => void;
  setBaseBranch: (value: string) => void;
  setBranchName: (value: string) => void;
  setTestsCommand: (value: string) => void;
  setIssueUrl: (value: string) => void;
  setIssueNumber: (value: string) => void;
  setIssueTitle: (value: string) => void;
  setIssueBody: (value: string) => void;
  submit: (event: FormEvent) => Promise<void>;
  refreshActiveTask: () => Promise<void>;
  reset: () => void;
}

const isTerminalStatus = (status: string) => ['pr_opened', 'failed', 'cancelled'].includes(status);

export const useAgentTaskForm = (): AgentTaskFormState => {
  const { showSuccess, showError } = useToast();
  const [task, setTask] = useState('');
  const [repoUrl, setRepoUrl] = useState('');
  const [baseBranch, setBaseBranch] = useState('main');
  const [branchName, setBranchName] = useState('');
  const [testsCommand, setTestsCommand] = useState('make test-critical');
  const [issueUrl, setIssueUrl] = useState('');
  const [issueNumber, setIssueNumber] = useState('');
  const [issueTitle, setIssueTitle] = useState('');
  const [issueBody, setIssueBody] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTask, setActiveTask] = useState<AgentTaskRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const normalizedIssueNumber = useMemo(() => {
    const parsed = Number.parseInt(issueNumber, 10);
    return Number.isFinite(parsed) ? parsed : null;
  }, [issueNumber]);

  const refreshActiveTask = useCallback(async () => {
    if (!activeTask) return;
    setRefreshing(true);
    try {
      const [taskRecord, events] = await Promise.all([
        getAgentTask(activeTask.task_id),
        getAgentTaskEvents(activeTask.task_id),
      ]);
      setActiveTask({
        ...taskRecord,
        events: events.events,
      });
    } catch (err) {
      const uiError = toUiError(err, {
        code: 'AGENT_TASK_REFRESH_FAILED',
        userMessage: getUserMessage(err),
      });
      setError(uiError.userMessage);
    } finally {
      setRefreshing(false);
    }
  }, [activeTask, showError]);

  const submit = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      const trimmedTask = task.trim();
      if (!trimmedTask) return;

      setError(null);
      setSubmitting(true);
      try {
        const record = await submitAgentTask({
          task: trimmedTask,
          repo_url: repoUrl.trim() || undefined,
          base_branch: baseBranch.trim() || undefined,
          branch_name: branchName.trim() || undefined,
          tests_command: testsCommand.trim() || undefined,
          source: 'ui',
          issue_url: issueUrl.trim() || undefined,
          issue_number: normalizedIssueNumber ?? undefined,
          issue_title: issueTitle.trim() || undefined,
          issue_body: issueBody.trim() || undefined,
          metadata: {
            submitted_from: 'web-agent-screen',
          },
        });

        setActiveTask(record);
        setTask('');
        showSuccess('Agent task submitted', 'The task is queued for the Sprite worker.');
      } catch (err) {
        const uiError = toUiError(err, {
          code: 'AGENT_TASK_SUBMIT_FAILED',
          userMessage: getUserMessage(err),
        });
        setError(uiError.userMessage);
        showError('Agent task failed', uiError.userMessage);
      } finally {
        setSubmitting(false);
      }
    },
    [
      baseBranch,
      branchName,
      issueBody,
      issueNumber,
      issueTitle,
      issueUrl,
      normalizedIssueNumber,
      repoUrl,
      showError,
      showSuccess,
      task,
      testsCommand,
    ]
  );

  useEffect(() => {
    if (!activeTask || isTerminalStatus(activeTask.status)) return;
    const timer = window.setInterval(() => {
      void refreshActiveTask();
    }, 3000);
    return () => window.clearInterval(timer);
  }, [activeTask, refreshActiveTask]);

  const reset = useCallback(() => {
    setTask('');
    setRepoUrl('');
    setBaseBranch('main');
    setBranchName('');
    setTestsCommand('make test-critical');
    setIssueUrl('');
    setIssueNumber('');
    setIssueTitle('');
    setIssueBody('');
    setActiveTask(null);
    setError(null);
  }, []);

  return {
    task,
    repoUrl,
    baseBranch,
    branchName,
    testsCommand,
    issueUrl,
    issueNumber,
    issueTitle,
    issueBody,
    submitting,
    refreshing,
    activeTask,
    error,
    setTask,
    setRepoUrl,
    setBaseBranch,
    setBranchName,
    setTestsCommand,
    setIssueUrl,
    setIssueNumber,
    setIssueTitle,
    setIssueBody,
    submit,
    refreshActiveTask,
    reset,
  };
};
