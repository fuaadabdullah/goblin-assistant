import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import AgentTaskView from '../AgentTaskView';

const session = {
  task: 'add rate limiting',
  repoUrl: 'https://github.com/acme/goblin-assistant',
  baseBranch: 'main',
  branchName: 'agent/add-rate-limiting',
  testsCommand: 'make test-critical',
  issueUrl: 'https://github.com/acme/goblin-assistant/issues/42',
  issueNumber: '42',
  issueTitle: 'Add rate limiting',
  issueBody: 'Throttle the chat route.',
  submitting: false,
  refreshing: false,
  activeTask: {
    task_id: 'task-1',
    status: 'pr_opened',
    phase: 'publishing',
    source: 'ui',
    task: 'add rate limiting',
    repo_url: 'https://github.com/acme/goblin-assistant',
    base_branch: 'main',
    branch_name: 'agent/add-rate-limiting',
    tests_command: 'make test-critical',
    issue_url: 'https://github.com/acme/goblin-assistant/issues/42',
    issue_number: 42,
    issue_title: 'Add rate limiting',
    issue_body: 'Throttle the chat route.',
    worker_status: 'accepted',
    worker_error: null,
    pr_url: 'https://github.com/acme/goblin-assistant/pull/123',
    callback_url: 'http://127.0.0.1:8001/api/v1/agent/task/task-1/events',
    workspace_id: 'workspace-github-com-acme-goblin-assistant-main',
    workspace_family: 'github.com/acme/goblin-assistant@main',
    sprite_name: 'sprite-github-com-acme-goblin-assistant-main',
    checkout_ref: 'main',
    workspace_provider: 'fly.io',
    architect_model: 'router-reason',
    editor_model: 'router-code',
    aider_mode: 'architect',
    auto_commit_each_change: true,
    repair_attempts: 2,
    phase0_ci_commands: [
      { name: 'pytest', command: 'cd apps/api && PYTHONPATH=src python3.11 -m pytest -o "addopts=" -v' },
      { name: 'lint', command: 'make lint' },
      { name: 'build', command: 'make build' },
    ],
    created_at: '2026-07-03T00:00:00Z',
    updated_at: '2026-07-03T00:01:00Z',
    events: [
      {
        event_id: 'event-1',
        type: 'task.created',
        message: 'Agent task queued for worker dispatch',
        timestamp: '2026-07-03T00:00:00Z',
        metadata: {},
      },
      {
        event_id: 'event-2',
        type: 'worker.accepted',
        message: 'Worker accepted task',
        timestamp: '2026-07-03T00:00:10Z',
        metadata: {},
      },
    ],
    payload: {},
    metadata: {},
    result: {},
  },
  error: null,
  setTask: vi.fn(),
  setRepoUrl: vi.fn(),
  setBaseBranch: vi.fn(),
  setBranchName: vi.fn(),
  setTestsCommand: vi.fn(),
  setIssueUrl: vi.fn(),
  setIssueNumber: vi.fn(),
  setIssueTitle: vi.fn(),
  setIssueBody: vi.fn(),
  submit: vi.fn(),
  refreshActiveTask: vi.fn(),
  reset: vi.fn(),
};

describe('AgentTaskView', () => {
  it('renders the active task state and pull request link', () => {
    render(<AgentTaskView session={session} />);

    expect(screen.getByText('pr_opened')).toBeInTheDocument();
    expect(screen.getByText('publishing')).toBeInTheDocument();
    expect(screen.getByText('task-1')).toBeInTheDocument();
    expect(screen.getByText('Open pull request')).toHaveAttribute(
      'href',
      'https://github.com/acme/goblin-assistant/pull/123'
    );
    expect(screen.getByText('worker.accepted')).toBeInTheDocument();
    expect(screen.getByText('workspace-github-com-acme-goblin-assistant-main')).toBeInTheDocument();
    expect(screen.getByText('sprite-github-com-acme-goblin-assistant-main')).toBeInTheDocument();
    expect(screen.getAllByText('router-reason').length).toBeGreaterThan(0);
    expect(screen.getAllByText('router-code').length).toBeGreaterThan(0);
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('3 commands')).toBeInTheDocument();
  });
});
