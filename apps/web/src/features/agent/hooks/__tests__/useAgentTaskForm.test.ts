import { renderHook, act } from '@testing-library/react';

import type { AgentTaskEventsResponse, AgentTaskRecord } from '../../../../lib/api/api-types';
import { useAgentTaskForm } from '../useAgentTaskForm';

const {
  mockSubmitAgentTask,
  mockGetAgentTask,
  mockGetAgentTaskEvents,
  mockShowSuccess,
  mockShowError,
  mockGetUserMessage,
  mockToUiError,
} = vi.hoisted(() => ({
  mockSubmitAgentTask: vi.fn(),
  mockGetAgentTask: vi.fn(),
  mockGetAgentTaskEvents: vi.fn(),
  mockShowSuccess: vi.fn(),
  mockShowError: vi.fn(),
  mockGetUserMessage: vi.fn(() => 'Unable to process the agent task.'),
  mockToUiError: vi.fn((_error: unknown, fallback: { code: string; userMessage: string }) => ({
    code: fallback.code,
    userMessage: fallback.userMessage,
  })),
}));

vi.mock('../../api', () => ({
  submitAgentTask: mockSubmitAgentTask,
  getAgentTask: mockGetAgentTask,
  getAgentTaskEvents: mockGetAgentTaskEvents,
}));

vi.mock('../../../../hooks/useToast', () => ({
  useToast: () => ({
    showSuccess: mockShowSuccess,
    showError: mockShowError,
  }),
}));

vi.mock('../../../../lib/ui-error', () => ({
  toUiError: mockToUiError,
}));

vi.mock('../../../../lib/error/toast', () => ({
  getUserMessage: mockGetUserMessage,
}));

function makeTaskRecord(overrides: Partial<AgentTaskRecord> = {}): AgentTaskRecord {
  return {
    task_id: 'task-1',
    status: 'running',
    phase: 'publishing',
    source: 'ui',
    task: 'add rate limiting',
    repo_url: 'https://github.com/acme/goblin-assistant',
    base_branch: 'main',
    branch_name: 'agent/add-rate-limiting',
    tests_command: 'make test-critical',
    created_at: '2026-07-17T00:00:00Z',
    updated_at: '2026-07-17T00:00:00Z',
    events: [],
    payload: {},
    metadata: {},
    result: {},
    ...overrides,
  };
}

describe('useAgentTaskForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();
  });

  it('starts with the expected defaults and reset restores them', () => {
    const { result } = renderHook(() => useAgentTaskForm());

    expect(result.current.task).toBe('');
    expect(result.current.repoUrl).toBe('');
    expect(result.current.baseBranch).toBe('main');
    expect(result.current.testsCommand).toBe('make test-critical');
    expect(result.current.activeTask).toBeNull();

    act(() => {
      result.current.setTask('Investigate');
      result.current.setRepoUrl('https://github.com/acme/repo');
      result.current.setBaseBranch('develop');
      result.current.setBranchName('feature/agent-task');
      result.current.setTestsCommand('pnpm test');
      result.current.setIssueUrl('https://github.com/acme/repo/issues/1');
      result.current.setIssueNumber('12');
      result.current.setIssueTitle('Add rate limiting');
      result.current.setIssueBody('Throttle the chat route.');
    });

    act(() => {
      result.current.reset();
    });

    expect(result.current.task).toBe('');
    expect(result.current.repoUrl).toBe('');
    expect(result.current.baseBranch).toBe('main');
    expect(result.current.branchName).toBe('');
    expect(result.current.testsCommand).toBe('make test-critical');
    expect(result.current.issueUrl).toBe('');
    expect(result.current.issueNumber).toBe('');
    expect(result.current.issueTitle).toBe('');
    expect(result.current.issueBody).toBe('');
    expect(result.current.activeTask).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('ignores empty submissions', async () => {
    const { result } = renderHook(() => useAgentTaskForm());

    await act(async () => {
      await result.current.submit({ preventDefault: vi.fn() } as never);
    });

    expect(mockSubmitAgentTask).not.toHaveBeenCalled();
    expect(mockShowSuccess).not.toHaveBeenCalled();
    expect(mockShowError).not.toHaveBeenCalled();
  });

  it('submits trimmed task data, stores the active task, and refreshes it on the timer', async () => {
    const initialTask = makeTaskRecord({ status: 'running' });
    const refreshedTask = makeTaskRecord({
      status: 'running',
      events: [
        {
          event_id: 'event-2',
          type: 'worker.running',
          message: 'Still running',
          timestamp: '2026-07-17T00:03:00Z',
          metadata: {},
        },
      ],
    });
    const eventsResponse: AgentTaskEventsResponse = {
      task_id: 'task-1',
      status: 'running',
      phase: 'publishing',
      events: refreshedTask.events,
      total: refreshedTask.events.length,
    };

    mockSubmitAgentTask.mockResolvedValueOnce(initialTask);
    mockGetAgentTask.mockResolvedValue(refreshedTask);
    mockGetAgentTaskEvents.mockResolvedValue(eventsResponse);

    const { result, unmount } = renderHook(() => useAgentTaskForm());

    act(() => {
      result.current.setTask('  add rate limiting  ');
      result.current.setRepoUrl('  https://github.com/acme/goblin-assistant  ');
      result.current.setBaseBranch(' main ');
      result.current.setBranchName(' feature/rate-limit ');
      result.current.setTestsCommand(' make test-critical ');
      result.current.setIssueUrl(' https://github.com/acme/goblin-assistant/issues/42 ');
      result.current.setIssueNumber('42');
      result.current.setIssueTitle(' Add rate limiting ');
      result.current.setIssueBody(' Throttle the chat route. ');
    });

    await act(async () => {
      await result.current.submit({ preventDefault: vi.fn() } as never);
    });

    expect(mockSubmitAgentTask).toHaveBeenCalledWith({
      task: 'add rate limiting',
      repo_url: 'https://github.com/acme/goblin-assistant',
      base_branch: 'main',
      branch_name: 'feature/rate-limit',
      tests_command: 'make test-critical',
      source: 'ui',
      issue_url: 'https://github.com/acme/goblin-assistant/issues/42',
      issue_number: 42,
      issue_title: 'Add rate limiting',
      issue_body: 'Throttle the chat route.',
      metadata: {
        submitted_from: 'web-agent-screen',
      },
    });
    expect(mockShowSuccess).toHaveBeenCalledWith(
      'Agent task submitted',
      'The task is queued for the Sprite worker.'
    );
    expect(result.current.task).toBe('');
    expect(result.current.activeTask?.task_id).toBe('task-1');
    expect(result.current.error).toBeNull();

    await act(async () => {
      await result.current.refreshActiveTask();
    });

    expect(mockGetAgentTask).toHaveBeenCalledWith('task-1');
    expect(mockGetAgentTaskEvents).toHaveBeenCalledWith('task-1');
    expect(result.current.activeTask?.events).toHaveLength(1);

    unmount();
  });

  it('does not schedule a refresh for terminal tasks', async () => {
    vi.useFakeTimers();

    mockSubmitAgentTask.mockResolvedValueOnce(makeTaskRecord({ status: 'pr_opened' }));

    const { result, unmount } = renderHook(() => useAgentTaskForm());

    act(() => {
      result.current.setTask('add rate limiting');
    });

    await act(async () => {
      await result.current.submit({ preventDefault: vi.fn() } as never);
    });

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(mockGetAgentTask).not.toHaveBeenCalled();
    expect(mockGetAgentTaskEvents).not.toHaveBeenCalled();

    unmount();
  });

  it('surfaces submit failures and refresh failures', async () => {
    const failedSubmit = new Error('submit failed');
    mockSubmitAgentTask.mockRejectedValueOnce(failedSubmit);
    mockToUiError.mockImplementationOnce((_error, fallback) => ({
      code: fallback.code,
      userMessage: 'Unable to process the agent task.',
    }));

    const { result } = renderHook(() => useAgentTaskForm());

    act(() => {
      result.current.setTask('add rate limiting');
    });

    await act(async () => {
      await result.current.submit({ preventDefault: vi.fn() } as never);
    });

    expect(result.current.error).toBe('Unable to process the agent task.');
    expect(mockShowError).toHaveBeenCalledWith(
      'Agent task failed',
      'Unable to process the agent task.'
    );

    mockGetAgentTask.mockRejectedValueOnce(new Error('refresh failed'));
    mockGetAgentTaskEvents.mockResolvedValueOnce({
      task_id: 'task-1',
      status: 'running',
      phase: 'publishing',
      events: [],
      total: 0,
    });
    mockGetUserMessage.mockReturnValueOnce('Could not refresh task.');
    mockToUiError.mockImplementationOnce((_error, fallback) => ({
      code: fallback.code,
      userMessage: 'Could not refresh task.',
    }));

    act(() => {
      result.current.setTask('add rate limiting');
    });

    mockSubmitAgentTask.mockResolvedValueOnce(makeTaskRecord());
    await act(async () => {
      await result.current.submit({ preventDefault: vi.fn() } as never);
    });

    await act(async () => {
      await result.current.refreshActiveTask();
    });

    expect(result.current.error).toBe('Could not refresh task.');
  });
});
