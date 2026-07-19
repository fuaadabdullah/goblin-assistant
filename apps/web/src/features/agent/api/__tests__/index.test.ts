import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  mockSubmitAgentTask,
  mockGetAgentTask,
  mockGetAgentTaskEvents,
  mockSubmitGithubIssueWebhook,
} = vi.hoisted(() => ({
  mockSubmitAgentTask: vi.fn(),
  mockGetAgentTask: vi.fn(),
  mockGetAgentTaskEvents: vi.fn(),
  mockSubmitGithubIssueWebhook: vi.fn(),
}));

vi.mock('@/lib/api', () => ({
  apiClient: {
    submitAgentTask: mockSubmitAgentTask,
    getAgentTask: mockGetAgentTask,
    getAgentTaskEvents: mockGetAgentTaskEvents,
    submitGithubIssueWebhook: mockSubmitGithubIssueWebhook,
  },
}));

import {
  getAgentTask,
  getAgentTaskEvents,
  submitAgentTask,
  submitGithubIssueWebhook,
} from '../index';

describe('agent api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('preserves submit failures', async () => {
    mockSubmitAgentTask.mockRejectedValueOnce(new Error('worker offline'));

    await expect(
      submitAgentTask({ task: 'add rate limiting', repo_url: 'https://github.com/acme/repo' })
    ).rejects.toMatchObject({
      code: 'AGENT_TASK_SUBMIT_FAILED',
      userMessage: 'worker offline',
    });
  });

  it('returns task records and event payloads', async () => {
    mockGetAgentTask.mockResolvedValueOnce({ task_id: 'task-1' });
    mockGetAgentTaskEvents.mockResolvedValueOnce({
      task_id: 'task-1',
      status: 'queued',
      phase: 'queued',
      events: [],
      total: 0,
    });
    mockSubmitGithubIssueWebhook.mockResolvedValueOnce({ accepted: true, ignored: false });

    await expect(getAgentTask('task-1')).resolves.toEqual({ task_id: 'task-1' });
    await expect(getAgentTaskEvents('task-1')).resolves.toMatchObject({
      task_id: 'task-1',
      total: 0,
    });
    await expect(submitGithubIssueWebhook({ action: 'opened' })).resolves.toMatchObject({
      accepted: true,
    });
  });
});
