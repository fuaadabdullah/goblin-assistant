import React, { act } from 'react';
import { createRoot, Root } from 'react-dom/client';
import { ProviderProvider, useProvider } from '../ProviderContext';

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
  const originalFetch = global.fetch;
  let container: HTMLDivElement;
  let root: Root;

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
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  afterAll(() => {
    global.fetch = originalFetch;
  });

  test('loads providers/models from /api/models', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
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
      }),
    });
    global.fetch = fetchMock as typeof fetch;

    act(() => {
      root.render(
        <ProviderProvider>
          <Probe />
        </ProviderProvider>,
      );
    });

    await waitForAssertion(() => {
      expect(getByTestId('providers').textContent).toBe('openai,ollama_gcp');
    });
    expect(getByTestId('selected-provider').textContent).toBe('openai');
    expect(getByTestId('models').textContent).toContain('gpt-4o-mini');
    expect(getByTestId('models').textContent).toContain('qwen2.5:3b');
    expect(getByTestId('provider-error').textContent).toBe('');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith('/api/models');
  });

  test('keeps empty provider/model lists for empty backend registry', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        models: [],
        source: 'empty',
      }),
    });
    global.fetch = fetchMock as typeof fetch;

    act(() => {
      root.render(
        <ProviderProvider>
          <Probe />
        </ProviderProvider>,
      );
    });

    await waitForAssertion(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });
    expect(getByTestId('providers').textContent).toBe('');
    expect(getByTestId('selected-provider').textContent).toBe('');
    expect(getByTestId('models').textContent).toBe('');
    expect(getByTestId('provider-error').textContent).toBe('');
  });

  test('does not use static fallback providers when /api/models fails', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: false,
      status: 503,
      statusText: 'Service Unavailable',
    });
    global.fetch = fetchMock as typeof fetch;

    act(() => {
      root.render(
        <ProviderProvider>
          <Probe />
        </ProviderProvider>,
      );
    });

    await waitForAssertion(() => {
      expect(getByTestId('provider-error').textContent).toContain(
        'Failed to fetch model registry',
      );
    });
    expect(getByTestId('providers').textContent).toBe('');
    expect(getByTestId('selected-provider').textContent).toBe('');
    expect(getByTestId('models').textContent).toBe('');
  });

  test('normalizes provider ids to backend canonical format', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        providers: [
          { id: 'azure-openai', health: 'healthy', is_selectable: true },
          { id: 'ali-baba', health: 'unhealthy', is_selectable: false },
        ],
        models: [
          { provider: 'azure-openai', name: 'gpt-4o' },
          { provider: 'ali-baba', name: 'qwen2.5:3b' },
        ],
      }),
    });
    global.fetch = fetchMock as typeof fetch;

    act(() => {
      root.render(
        <ProviderProvider>
          <Probe />
        </ProviderProvider>,
      );
    });

    await waitForAssertion(() => {
      expect(getByTestId('providers').textContent).toBe('azure_openai,aliyun');
    });
    expect(getByTestId('selected-provider').textContent).toBe('azure_openai');
    expect(getByTestId('provider-error').textContent).toBe('');
  });
});
