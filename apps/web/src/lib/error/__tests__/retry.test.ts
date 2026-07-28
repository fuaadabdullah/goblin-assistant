const { mockIsRetryable } = vi.hoisted(() => ({
  mockIsRetryable: vi.fn(),
}));

vi.mock('../handler', () => ({
  isRetryable: mockIsRetryable,
}));

import { withRetry } from '../retry';

describe('withRetry', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsRetryable.mockReturnValue(true);
    vi.spyOn(Math, 'random').mockReturnValue(0);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('retries once with backoff before succeeding', async () => {
    const fn = vi.fn().mockRejectedValueOnce(new Error('transient')).mockResolvedValueOnce('ok');

    const promise = withRetry(fn, {
      maxAttempts: 2,
      baseDelayMs: 25,
      shouldRetry: () => true,
    });

    await vi.advanceTimersByTimeAsync(25);
    await expect(promise).resolves.toBe('ok');
    expect(fn).toHaveBeenCalledTimes(2);
  });

  it('stops immediately when retries are disabled', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('no retry'));

    await expect(
      withRetry(fn, {
        maxAttempts: 3,
        shouldRetry: () => false,
      })
    ).rejects.toThrow('no retry');

    expect(fn).toHaveBeenCalledTimes(1);
  });
});
