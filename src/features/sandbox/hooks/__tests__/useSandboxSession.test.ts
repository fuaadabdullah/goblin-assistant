import { renderHook, act } from '@testing-library/react';

jest.mock('../../api', () => ({
  fetchSandboxJobs: jest.fn(),
  fetchJobLogs: jest.fn(),
  runSandboxCode: jest.fn(),
}));

jest.mock('../../../../lib/ui-error', () => ({
  toUiError: jest.fn((_err: unknown, opts: { userMessage: string }) => ({
    userMessage: opts.userMessage,
  })),
}));

jest.mock('@/utils/dev-log', () => ({ devError: jest.fn() }));

import { useSandboxSession } from '../useSandboxSession';
import { fetchSandboxJobs, fetchJobLogs, runSandboxCode } from '../../api';

const mockFetchJobs = fetchSandboxJobs as jest.Mock;
const mockFetchLogs = fetchJobLogs as jest.Mock;
const mockRunCode = runSandboxCode as jest.Mock;

describe('useSandboxSession', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetchJobs.mockResolvedValue([]);
  });

  it('returns initial state', () => {
    const { result } = renderHook(() => useSandboxSession());
    expect(result.current.code).toBe('');
    expect(result.current.language).toBe('python');
    expect(result.current.logs).toBe('');
    expect(result.current.loading).toBe(false);
    expect(result.current.selectedJob).toBeNull();
  });

  it('fetches jobs on mount for non-guest', async () => {
    const jobs = [{ id: 'j1', status: 'done', created_at: '2024-01-01' }];
    mockFetchJobs.mockResolvedValue(jobs);
    const { result } = renderHook(() => useSandboxSession());
    await act(async () => {});
    expect(mockFetchJobs).toHaveBeenCalled();
  });

  it('does not fetch jobs for guest', async () => {
    const { result } = renderHook(() => useSandboxSession({ isGuest: true }));
    await act(async () => {});
    expect(mockFetchJobs).not.toHaveBeenCalled();
    expect(result.current.jobs).toEqual([]);
  });

  it('setCode updates code', () => {
    const { result } = renderHook(() => useSandboxSession());
    act(() => result.current.setCode('print("hi")'));
    expect(result.current.code).toBe('print("hi")');
  });

  it('setLanguage updates language', () => {
    const { result } = renderHook(() => useSandboxSession());
    act(() => result.current.setLanguage('javascript'));
    expect(result.current.language).toBe('javascript');
  });

  it('clearCode resets code to empty', () => {
    const { result } = renderHook(() => useSandboxSession());
    act(() => result.current.setCode('some code'));
    act(() => result.current.clearCode());
    expect(result.current.code).toBe('');
  });

  it('runCode does nothing when code is empty', async () => {
    const { result } = renderHook(() => useSandboxSession());
    await act(async () => { await result.current.runCode(); });
    expect(mockRunCode).not.toHaveBeenCalled();
  });

  it('runCode executes code and sets logs', async () => {
    mockRunCode.mockResolvedValue('output: 42');
    mockFetchJobs.mockResolvedValue([]);
    const { result } = renderHook(() => useSandboxSession());
    act(() => result.current.setCode('print(42)'));
    await act(async () => { await result.current.runCode(); });
    expect(mockRunCode).toHaveBeenCalledWith({ code: 'print(42)', language: 'python' });
    expect(result.current.logs).toBe('output: 42');
    expect(result.current.loading).toBe(false);
  });

  it('runCode sets error message on failure', async () => {
    mockRunCode.mockRejectedValue(new Error('timeout'));
    const { result } = renderHook(() => useSandboxSession());
    act(() => result.current.setCode('bad code'));
    await act(async () => { await result.current.runCode(); });
    expect(result.current.logs).toBe('Unable to run that code right now.');
    expect(result.current.loading).toBe(false);
  });

  it('selectJob fetches and displays logs', async () => {
    const job = { id: 'j1', status: 'done' as const, created_at: '2024-01-01' };
    mockFetchLogs.mockResolvedValue({ stdout: 'hello' });
    const { result } = renderHook(() => useSandboxSession());
    await act(async () => { await result.current.selectJob(job); });
    expect(mockFetchLogs).toHaveBeenCalledWith('j1');
    expect(result.current.logs).toContain('hello');
  });

  it('selectJob shows guest message for guest', async () => {
    const job = { id: 'j1', status: 'done' as const, created_at: '2024-01-01' };
    const { result } = renderHook(() => useSandboxSession({ isGuest: true }));
    await act(async () => { await result.current.selectJob(job); });
    expect(mockFetchLogs).not.toHaveBeenCalled();
    expect(result.current.logs).toContain('Sign in');
  });

  it('selectJob sets error on failure', async () => {
    const job = { id: 'j1', status: 'done' as const, created_at: '2024-01-01' };
    mockFetchLogs.mockRejectedValue(new Error('not found'));
    const { result } = renderHook(() => useSandboxSession());
    await act(async () => { await result.current.selectJob(job); });
    expect(result.current.logs).toBe('Unable to load logs for that job.');
  });

  it('refreshJobs reloads job list', async () => {
    mockFetchJobs.mockResolvedValue([{ id: 'j2', status: 'running', created_at: '2024-01-02' }]);
    const { result } = renderHook(() => useSandboxSession());
    await act(async () => { await result.current.refreshJobs(); });
    expect(mockFetchJobs).toHaveBeenCalled();
  });

  it('refreshJobs handles error gracefully', async () => {
    mockFetchJobs.mockRejectedValue(new Error('network'));
    const { result } = renderHook(() => useSandboxSession());
    await act(async () => { await result.current.refreshJobs(); });
    // Should not throw
  });
});
