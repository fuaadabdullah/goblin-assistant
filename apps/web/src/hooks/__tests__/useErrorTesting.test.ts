import { renderHook, act } from '@testing-library/react';

vi.mock('@sentry/react', () => ({
  captureException: vi.fn().mockReturnValue('event-id-1'),
  captureMessage: vi.fn().mockReturnValue('event-id-2'),
  addBreadcrumb: vi.fn(),
}));

import * as Sentry from '@sentry/react';
import { formatErrorTestMessage, useErrorTesting } from '../useErrorTesting';

// Mock fetch for network error test
const originalFetch = global.fetch;
beforeAll(() => {
  global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 });
});
afterAll(() => {
  global.fetch = originalFetch;
});

describe('useErrorTesting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns initial state', () => {
    const { result } = renderHook(() => useErrorTesting());
    expect(result.current.isLoading).toBe(false);
    expect(result.current.results).toEqual([]);
  });

  it('testJavaScriptError adds a result', async () => {
    const { result } = renderHook(() => useErrorTesting());
    await act(async () => {
      await result.current.testJavaScriptError();
    });
    expect(result.current.results).toHaveLength(1);
    expect(result.current.results[0].label).toBe('JavaScript Error');
    expect(result.current.results[0].status).toBe('failed');
  });

  it('testAsyncError adds a result', async () => {
    const { result } = renderHook(() => useErrorTesting());
    await act(async () => {
      await result.current.testAsyncError();
    });
    expect(result.current.results).toHaveLength(1);
    expect(result.current.results[0].label).toBe('Async Error');
    expect(result.current.results[0].status).toBe('failed');
  });

  it('testNetworkError adds a result', async () => {
    const { result } = renderHook(() => useErrorTesting());
    await act(async () => {
      await result.current.testNetworkError();
    });
    expect(result.current.results).toHaveLength(1);
    expect(result.current.results[0].label).toBe('Network Error');
    expect(result.current.results[0].status).toBe('failed');
  });

  it('testTypeError adds a failed result', async () => {
    const { result } = renderHook(() => useErrorTesting());
    await act(async () => {
      await result.current.testTypeError();
    });
    expect(result.current.results).toHaveLength(1);
    expect(result.current.results[0].label).toBe('Type Error');
    expect(result.current.results[0].status).toBe('failed');
  });

  it('preserves non-Error failure messages', () => {
    expect(formatErrorTestMessage('registry unavailable')).toBe('registry unavailable');
  });

  it('testCustomError adds a result', async () => {
    const { result } = renderHook(() => useErrorTesting());
    await act(async () => {
      await result.current.testCustomError();
    });
    expect(result.current.results).toHaveLength(1);
    expect(result.current.results[0].label).toBe('Custom Error');
  });

  it('testSentryError captures exception via Sentry', async () => {
    const { result } = renderHook(() => useErrorTesting());
    await act(async () => {
      await result.current.testSentryError();
    });
    expect(Sentry.captureException).toHaveBeenCalledWith(expect.any(Error));
    expect(result.current.results[0].status).toBe('success');
  });

  it('testSentryMessage captures message via Sentry', async () => {
    const { result } = renderHook(() => useErrorTesting());
    await act(async () => {
      await result.current.testSentryMessage();
    });
    expect(Sentry.captureMessage).toHaveBeenCalledWith('Sentry test message', 'info');
  });

  it('testSentryBreadcrumb adds breadcrumb and captures message', async () => {
    const { result } = renderHook(() => useErrorTesting());
    await act(async () => {
      await result.current.testSentryBreadcrumb();
    });
    expect(Sentry.addBreadcrumb).toHaveBeenCalledWith({
      message: 'Sentry breadcrumb',
      category: 'test',
      level: 'info',
    });
  });

  it('runAllTests runs all tests and restores loading state', async () => {
    const { result } = renderHook(() => useErrorTesting());
    await act(async () => {
      await result.current.runAllTests();
    });
    expect(result.current.isLoading).toBe(false);
    expect(result.current.results).toHaveLength(9);
    expect(result.current.results.map((item) => item.label)).toEqual([
      'JavaScript Error',
      'Type Error',
      'Custom Error',
      'Async Error',
      'Network Error',
      'Unhandled Promise Rejection',
      'Sentry Error',
      'Sentry Message',
      'Sentry Breadcrumb',
    ]);
  });

  it('clearResults empties the results array', async () => {
    const { result } = renderHook(() => useErrorTesting());
    await act(async () => {
      await result.current.testJavaScriptError();
    });
    expect(result.current.results.length).toBe(1);
    act(() => {
      result.current.clearResults();
    });
    expect(result.current.results).toEqual([]);
  });

  it('calls onSuccess callback when test succeeds', async () => {
    const onSuccess = vi.fn();
    const { result } = renderHook(() => useErrorTesting(onSuccess));
    await act(async () => {
      await result.current.testSentryError();
    });
    expect(onSuccess).toHaveBeenCalledWith('Test completed', 'Sentry Error');
  });

  it('testUnhandledPromiseRejection adds a failed result', async () => {
    const { result } = renderHook(() => useErrorTesting());
    await act(async () => {
      await result.current.testUnhandledPromiseRejection();
    });
    expect(result.current.results).toHaveLength(1);
    expect(result.current.results[0].label).toBe('Unhandled Promise Rejection');
    expect(result.current.results[0].status).toBe('failed');
  });
});
