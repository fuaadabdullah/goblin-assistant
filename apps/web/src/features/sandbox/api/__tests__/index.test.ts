import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockGetSandboxJobs, mockGetJobLogs, mockRunSandboxCode } = vi.hoisted(() => ({
  mockGetSandboxJobs: vi.fn(),
  mockGetJobLogs: vi.fn(),
  mockRunSandboxCode: vi.fn(),
}));

vi.mock('@/lib/api', () => ({
  apiClient: {
    getSandboxJobs: mockGetSandboxJobs,
    getJobLogs: mockGetJobLogs,
    runSandboxCode: mockRunSandboxCode,
  },
}));

import { fetchSandboxJobs, fetchJobLogs, runSandboxCode } from '../index';

describe('sandbox api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('preserves sandbox job load errors', async () => {
    mockGetSandboxJobs.mockRejectedValueOnce(new Error('Sandbox queue unavailable'));

    await expect(fetchSandboxJobs()).rejects.toMatchObject({
      code: 'SANDBOX_JOBS_FAILED',
      userMessage: 'Sandbox queue unavailable',
    });
  });

  it('preserves sandbox log load errors', async () => {
    mockGetJobLogs.mockRejectedValueOnce(new Error('Job logs offline'));

    await expect(fetchJobLogs('job-1')).rejects.toMatchObject({
      code: 'SANDBOX_LOGS_FAILED',
      userMessage: 'Job logs offline',
    });
  });

  it('preserves sandbox run errors', async () => {
    mockRunSandboxCode.mockRejectedValueOnce(new Error('Sandbox runner unavailable'));

    await expect(runSandboxCode({ code: 'print(1)', language: 'python' })).rejects.toMatchObject({
      code: 'SANDBOX_RUN_FAILED',
      userMessage: 'Sandbox runner unavailable',
    });
  });

  it('preserves non-Error sandbox job errors', async () => {
    mockGetSandboxJobs.mockRejectedValueOnce('sandbox jobs offline');

    await expect(fetchSandboxJobs()).rejects.toMatchObject({
      code: 'SANDBOX_JOBS_FAILED',
      userMessage: 'sandbox jobs offline',
    });
  });
});
