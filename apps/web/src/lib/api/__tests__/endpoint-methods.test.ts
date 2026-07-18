const { mockGetCsrfToken, mockGetFrontend, mockPostFrontend, mockWithAuth } = vi.hoisted(() => ({
  mockGetCsrfToken: vi.fn(),
  mockGetFrontend: vi.fn(),
  mockPostFrontend: vi.fn(),
  mockWithAuth: vi.fn(),
}));
const { mockGetAuthTokenForRequest } = vi.hoisted(() => ({
  mockGetAuthTokenForRequest: vi.fn(),
}));

vi.mock('../shared', () => ({
  AUTH_REQUEST_TIMEOUT_MS: 60_000,
  getCsrfToken: mockGetCsrfToken,
  getFrontend: mockGetFrontend,
  postFrontend: mockPostFrontend,
  withAuth: mockWithAuth,
}));
vi.mock('../../../utils/auth-session', () => ({
  getAuthTokenForRequest: mockGetAuthTokenForRequest,
}));

import { agentMethods } from '../agent';
import { authMethods } from '../auth';
import { loggingMethods } from '../logging';
import { sandboxMethods } from '../sandbox';
import { searchMethods } from '../search';
import { supportMethods } from '../support';

describe('API endpoint method shims', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCsrfToken.mockResolvedValue('csrf-token');
    mockGetFrontend.mockResolvedValue({ url: 'https://google.example/login' });
    mockPostFrontend.mockResolvedValue({ ok: true });
    mockWithAuth.mockReturnValue({ headers: { Authorization: 'Bearer token' } });
    mockGetAuthTokenForRequest.mockResolvedValue('resolved-session-token');
  });

  it('forwards auth requests through the shared HTTP helpers', async () => {
    await expect(authMethods.passkeyChallenge('user@example.com')).resolves.toEqual({ ok: true });
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/auth/passkey/challenge', {
      email: 'user@example.com',
    });

    await authMethods.passkeyRegister('user@example.com', { id: 'credential' } as never);
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/auth/passkey/register', {
      email: 'user@example.com',
      credential: { id: 'credential' },
    });

    await authMethods.passkeyAuth('user@example.com', { id: 'assertion' } as never);
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/auth/passkey/auth', {
      email: 'user@example.com',
      assertion: { id: 'assertion' },
    });

    await authMethods.register('user@example.com', 'secret', 'captcha-token');
    expect(mockGetCsrfToken).toHaveBeenCalledTimes(1);
    expect(mockPostFrontend).toHaveBeenCalledWith(
      '/api/auth/register',
      {
        email: 'user@example.com',
        password: 'secret',
        turnstileToken: 'captcha-token',
        csrf_token: 'csrf-token',
      },
      { timeout: 60_000 }
    );

    await authMethods.login('user@example.com', 'secret');
    expect(mockGetCsrfToken).toHaveBeenCalledTimes(2);
    expect(mockPostFrontend).toHaveBeenCalledWith(
      '/api/auth/login',
      {
        email: 'user@example.com',
        password: 'secret',
        csrf_token: 'csrf-token',
      },
      { timeout: 60_000 }
    );

    await authMethods.validateToken('jwt-token');
    expect(mockPostFrontend).toHaveBeenCalledWith(
      '/api/auth/validate',
      { token: 'jwt-token' },
      {
        headers: {
          Authorization: 'Bearer jwt-token',
          'Content-Type': 'application/json',
        },
      }
    );

    await authMethods.validateToken();
    expect(mockGetAuthTokenForRequest).toHaveBeenCalledTimes(1);
    expect(mockPostFrontend).toHaveBeenCalledWith(
      '/api/auth/validate',
      { token: 'resolved-session-token' },
      {
        headers: {
          Authorization: 'Bearer resolved-session-token',
          'Content-Type': 'application/json',
        },
      }
    );

    await authMethods.logout();
    expect(mockWithAuth).toHaveBeenCalledTimes(1);
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/auth/logout', undefined, {
      headers: { Authorization: 'Bearer token' },
    });
  });

  it('maps Google auth URLs and surfaces missing URLs as errors', async () => {
    mockGetFrontend.mockResolvedValueOnce({ authorization_url: 'https://google.example/login' });
    await expect(authMethods.getGoogleAuthUrl()).resolves.toEqual({
      url: 'https://google.example/login',
    });

    mockGetFrontend.mockResolvedValueOnce({});
    await expect(authMethods.getGoogleAuthUrl()).rejects.toThrow(
      'Google sign-in URL is unavailable.'
    );
  });

  it('forwards agent, support, sandbox, search, and logging requests', async () => {
    await agentMethods.submitAgentTask({ task: 'ship it' } as never);
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/agent/task', { task: 'ship it' });

    await agentMethods.getAgentTask('task 1/2');
    expect(mockGetFrontend).toHaveBeenCalledWith('/api/agent/task/task%201%2F2');

    await agentMethods.getAgentTaskEvents('task 1/2');
    expect(mockGetFrontend).toHaveBeenCalledWith('/api/agent/task/task%201%2F2/events');

    await agentMethods.submitGithubIssueWebhook({ action: 'opened' });
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/agent/task/github-webhook', {
      action: 'opened',
    });

    await supportMethods.sendSupportMessage('help me');
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/support/message', {
      message: 'help me',
    });

    await supportMethods.triageIssue('The app is broken', 'chat');
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/support/triage', {
      description: 'The app is broken',
      context: 'chat',
    });

    await sandboxMethods.getSandboxJobs();
    expect(mockGetFrontend).toHaveBeenCalledWith('/api/sandbox/jobs');

    await sandboxMethods.getJobLogs('job 42');
    expect(mockGetFrontend).toHaveBeenCalledWith('/api/sandbox/jobs/job 42/logs');

    await sandboxMethods.runSandboxCode({
      code: 'print("hello")',
      language: 'python',
      timeout: 15,
    });
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/sandbox/run', {
      source: 'print("hello")',
      language: 'python',
      timeout: 15,
    });

    await searchMethods.getSearchCollections();
    expect(mockGetFrontend).toHaveBeenCalledWith('/api/search/collections');

    await searchMethods.searchQuery('docs', 'goblin assistant');
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/search/query', {
      collection: 'docs',
      query: 'goblin assistant',
      limit: 8,
    });

    await loggingMethods.getRaptorLogs(12);
    expect(mockGetFrontend).toHaveBeenCalledWith('/api/raptor/logs?limit=12');

    await loggingMethods.submitErrorReport({
      message: 'boom',
      timestamp: '2026-07-17T00:00:00.000Z',
      userAgent: 'test-agent',
      url: 'https://app.example/test',
    });
    expect(mockPostFrontend).toHaveBeenCalledWith('/api/errors', {
      message: 'boom',
      timestamp: '2026-07-17T00:00:00.000Z',
      userAgent: 'test-agent',
      url: 'https://app.example/test',
    });
  });
});
