import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
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
  const { providers, selectedProvider, models, providerConfigs, providerError } = useProvider();
  return (
    <div>
      <div data-testid="providers">{providers.join(',')}</div>
      <div data-testid="selected-provider">{selectedProvider}</div>
      <div data-testid="models">{models.join(',')}</div>
      <div data-testid="config-keys">{Array.from(providerConfigs.keys()).join(',')}</div>
      <div data-testid="provider-error">{providerError || ''}</div>
    </div>
  );
};

describe('ProviderContext', () => {
  let queryClient: QueryClient;

  const renderProbe = () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ProviderProvider>
          <Probe />
        </ProviderProvider>
      </QueryClientProvider>,
    );
  };

  beforeEach(() => {
    jest.resetAllMocks();
    localStorage.clear();
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  afterEach(() => {
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

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId('providers').textContent).toBe('openai,ollama_gcp');
      expect(screen.getByTestId('selected-provider').textContent).toBe('');
    });
    expect(screen.getByTestId('models').textContent).toContain('gpt-4o-mini');
    expect(screen.getByTestId('models').textContent).toContain('qwen2.5:3b');
    expect(screen.getByTestId('provider-error').textContent).toBe('');
    expect(mockGetModelConfigs).toHaveBeenCalledTimes(1);
  });

  test('keeps empty provider/model lists for empty backend registry', async () => {
    mockGetModelConfigs.mockResolvedValue({
      models: [],
      source: 'empty',
    });

    renderProbe();

    await waitFor(() => {
      expect(mockGetModelConfigs).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByTestId('providers').textContent).toBe('');
    expect(screen.getByTestId('selected-provider').textContent).toBe('');
    expect(screen.getByTestId('models').textContent).toBe('');
    expect(screen.getByTestId('provider-error').textContent).toBe('');
  });

  test('shows error when /api/models fails', async () => {
    mockGetModelConfigs.mockRejectedValue(new Error('Service Unavailable'));

    renderProbe();

    await waitFor(() => {
      // When the query fails, providers/models should be empty
      expect(mockGetModelConfigs).toHaveBeenCalled();
    });
    expect(screen.getByTestId('providers').textContent).toBe('');
    expect(screen.getByTestId('models').textContent).toBe('');
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

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId('providers').textContent).toBe('azure_openai');
    });
    expect(screen.getByTestId('config-keys').textContent).toBe('azure_openai,aliyun');
    expect(screen.getByTestId('selected-provider').textContent).toBe('');
    expect(screen.getByTestId('provider-error').textContent).toBe('');
  });

  test('restores a stored selectable provider preference', async () => {
    localStorage.setItem('selectedProvider', 'ollama-gcp');
    mockGetModelConfigs.mockResolvedValue({
      providers: [
        { id: 'openai', health: 'healthy', is_selectable: true },
        { id: 'ollama_gcp', health: 'healthy', is_selectable: true },
      ],
      models: [],
    });

    renderProbe();

    await waitFor(() => {
      expect(screen.getByTestId('selected-provider').textContent).toBe('ollama_gcp');
    });
  });
});
