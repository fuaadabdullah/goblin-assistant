import { createQueryClient } from '../queryClient';

describe('queryClient', () => {
  it('creates a QueryClient instance', () => {
    const client = createQueryClient();
    expect(client).toBeDefined();
    expect(typeof client.getDefaultOptions).toBe('function');
  });

  it('configures default query retry to 3', () => {
    const client = createQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.retry).toBe(3);
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

  it('configures mutation retry to 1', () => {
    const client = createQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.mutations?.retry).toBe(1);
  });
});
