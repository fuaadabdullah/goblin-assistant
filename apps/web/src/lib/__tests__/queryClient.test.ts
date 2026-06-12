import { createQueryClient } from '../queryClient';

describe('queryClient', () => {
  it('creates a QueryClient instance', () => {
    const client = createQueryClient();
    expect(client).toBeDefined();
    expect(typeof client.getDefaultOptions).toBe('function');
  });

  it('configures query retry to 3 attempts for retryable errors only', () => {
    const client = createQueryClient();
    const retry = client.getDefaultOptions().queries?.retry as (
      failureCount: number,
      error: unknown
    ) => boolean;
    expect(typeof retry).toBe('function');
    expect(retry(0, { status: 500 })).toBe(true);
    expect(retry(2, { status: 500 })).toBe(true);
    expect(retry(3, { status: 500 })).toBe(false);
    expect(retry(0, { status: 404 })).toBe(false);
  });

  it('configures staleTime to 5 minutes', () => {
    const client = createQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.staleTime).toBe(5 * 60 * 1000);
  });

  it('configures gcTime to 10 minutes', () => {
    const client = createQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.gcTime).toBe(10 * 60 * 1000);
  });

  it('disables refetchOnWindowFocus', () => {
    const client = createQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.refetchOnWindowFocus).toBe(false);
  });

  it('enables refetchOnReconnect', () => {
    const client = createQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.refetchOnReconnect).toBe(true);
  });

  it('configures mutation retry to 1 attempt for retryable errors only', () => {
    const client = createQueryClient();
    const retry = client.getDefaultOptions().mutations?.retry as (
      failureCount: number,
      error: unknown
    ) => boolean;
    expect(typeof retry).toBe('function');
    expect(retry(0, { status: 502 })).toBe(true);
    expect(retry(1, { status: 502 })).toBe(false);
    expect(retry(0, { status: 401 })).toBe(false);
  });
});
