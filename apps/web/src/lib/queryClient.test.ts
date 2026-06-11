import { createQueryClient } from './queryClient';

describe('createQueryClient', () => {
  it('creates a QueryClient instance', () => {
    const client = createQueryClient();
    expect(client).toBeDefined();
    expect(client.getQueryCache()).toBeDefined();
  });

  it('query retry allows up to 3 attempts for retryable errors only', () => {
    const client = createQueryClient();
    const retry = client.getDefaultOptions().queries?.retry as (
      failureCount: number,
      error: unknown
    ) => boolean;
    expect(typeof retry).toBe('function');
    const serverError = { status: 500 };
    const authError = { status: 401 };
    expect(retry(0, serverError)).toBe(true);
    expect(retry(2, serverError)).toBe(true);
    expect(retry(3, serverError)).toBe(false);
    expect(retry(0, authError)).toBe(false);
  });

  it('default options have staleTime of 5 minutes', () => {
    const client = createQueryClient();
    const options = client.getDefaultOptions();
    expect(options.queries?.staleTime).toBe(5 * 60 * 1000);
  });

  it('default options have gcTime of 10 minutes', () => {
    const client = createQueryClient();
    const options = client.getDefaultOptions();
    expect(options.queries?.gcTime).toBe(10 * 60 * 1000);
  });

  it('default options have refetchOnWindowFocus false', () => {
    const client = createQueryClient();
    const options = client.getDefaultOptions();
    expect(options.queries?.refetchOnWindowFocus).toBe(false);
  });

  it('default options have refetchOnReconnect true', () => {
    const client = createQueryClient();
    const options = client.getDefaultOptions();
    expect(options.queries?.refetchOnReconnect).toBe(true);
  });

  it('mutation retry allows 1 attempt for retryable errors only', () => {
    const client = createQueryClient();
    const retry = client.getDefaultOptions().mutations?.retry as (
      failureCount: number,
      error: unknown
    ) => boolean;
    expect(typeof retry).toBe('function');
    const serverError = { status: 503 };
    expect(retry(0, serverError)).toBe(true);
    expect(retry(1, serverError)).toBe(false);
    expect(retry(0, { status: 400 })).toBe(false);
  });
});
