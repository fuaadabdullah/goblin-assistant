import React, { act } from 'react';
import { createRoot, Root } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProviderProvider, useProvider } from '../ProviderContext';

/* Mock the API client used by useProviderHealth */
const mockGetModelConfigs = jest.fn();
jest.mock('@/api', () => ({
  apiClient: {
    getModelConfigs: (...args: unknown[]) => mockGetModelConfigs(...args),
  },
}));

const Probe = () => {
  const { providers, selectedProvider, models, providerError } = useProvider();
  return (
    <div>
      <div data-testid="providers">{providers.join(',')}</div>
      <div data-testid="selected-provider">{selectedProvider}</div>
      <div data-testid="models">{models.join(',')}</div>
      <div data-testid="provider-error">{providerError || ''}</div>
    </div>
  );
};

describe('ProviderContext', () => {
  let container: HTMLDivElement;
  let root: Root;
  let queryClient: QueryClient;

  const getByTestId = (testId: string): HTMLElement => {
    const node = container.querySelector(`[data-testid="${testId}"]`);
    if (!node) {
      throw new Error(`Missing test node: ${testId}`);
    }
    return node as HTMLElement;
  };

  const waitForAssertion = async (assertion: () => void): Promise<void> => {
    const timeoutMs = 2000;
    const startedAt = Date.now();
    let lastError: unknown;

    while (Date.now() - startedAt < timeoutMs) {
      try {
        assertion();
        return;
      } catch (error) {
        lastError = error;
      }

      await new Promise(resolve => setTimeout(resolve, 20));
    }

    throw lastError ?? new Error('Timed out waiting for assertion');
  };

  beforeEach(() => {
    jest.resetAllMocks();
    localStorage.clear();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    queryClient.clear();
  });

  test('loads providers/models from /api/models', async () => {
    mockGetModelConfigs.mockResolvedValue({
      providers: [
        { id: 'openai', health: 'healthy', is_selectable: true },
        { id: 'ollama_gcp', health: 'unknown', is_selectable: true },
      ],
      models: [
        { provider: 'openai', name: 'gpt-4o-mini' },
        { provider: 'openai', name: 'gpt-4o-mini' },
        { provider: 'ollama_gcp', name: 'qwen2.5:3b' },
      ],
      source: 'configured_with_health',
    });

    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ProviderProvider>
            <Probe />
          </ProviderProvider>
        </QueryClientProvider>,
      );
    });

    await waitForAssertion(() => {
      expect(getByTestId('providers').textContent).toBe('openai,ollama_gcp');
      expect(getByTestId('selected-provider').textContent).toBe('openai');
    });
    expect(getByTestId('models').textContent).toContain('gpt-4o-mini');
    expect(getByTestId('models').textContent).toContain('qwen2.5:3b');
    expect(getByTestId('provider-error').textContent).toBe('');
    expect(mockGetModelConfigs).toHaveBeenCalledTimes(1);
  });

  test('keeps empty provider/model lists for empty backend registry', async () => {
    mockGetModelConfigs.mockResolvedValue({
      models: [],
      source: 'empty',
    });

    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ProviderProvider>
            <Probe />
          </ProviderProvider>
        </QueryClientProvider>,
      );
    });

    await waitForAssertion(() => {
      expect(mockGetModelConfigs).toHaveBeenCalledTimes(1);
    });
    expect(getByTestId('providers').textContent).toBe('');
    expect(getByTestId('selected-provider').textContent).toBe('');
    expect(getByTestId('models').textContent).toBe('');
    expect(getByTestId('provider-error').textContent).toBe('');
  });

  test('shows error when /api/models fails', async () => {
    mockGetModelConfigs.mockRejectedValue(new Error('Service Unavailable'));

    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ProviderProvider>
            <Probe />
          </ProviderProvider>
        </QueryClientProvider>,
      );
    });

    await waitForAssertion(() => {
      // When the query fails, providers/models should be empty
      expect(mockGetModelConfigs).toHaveBeenCalled();
    });
    expect(getByTestId('providers').textContent).toBe('');
    expect(getByTestId('models').textContent).toBe('');
  });

  test('normalizes provider ids to backend canonical format', async () => {
    mockGetModelConfigs.mockResolvedValue({
      providers: [
        { id: 'azure-openai', health: 'healthy', is_selectable: true },
        { id: 'ali-baba', health: 'unhealthy', is_selectable: false },
      ],
      models: [
        { provider: 'azure-openai', name: 'gpt-4o' },
        { provider: 'ali-baba', name: 'qwen2.5:3b' },
      ],
    });

    act(() => {
      root.render(
        <QueryClientProvider client={queryClient}>
          <ProviderProvider>
            <Probe />
          </ProviderProvider>
        </QueryClientProvider>,
      );
    });

    await waitForAssertion(() => {
      expect(getByTestId('providers').textContent).toBe('azure_openai,aliyun');
    });
    expect(getByTestId('selected-provider').textContent).toBe('azure_openai');
    expect(getByTestId('provider-error').textContent).toBe('');
  });
});
