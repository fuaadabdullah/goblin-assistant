import { createQueryClient } from './queryClient';

describe('createQueryClient', () => {
  it('creates a QueryClient instance', () => {
    const client = createQueryClient();
    expect(client).toBeDefined();
    expect(client.getQueryCache()).toBeDefined();
  });

  it('default options have retry 3', () => {
    const client = createQueryClient();
    const options = client.getDefaultOptions();
    expect(options.queries?.retry).toBe(3);
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

  it('mutation retry is 1', () => {
    const client = createQueryClient();
    const options = client.getDefaultOptions();
    expect(options.mutations?.retry).toBe(1);
  });
});