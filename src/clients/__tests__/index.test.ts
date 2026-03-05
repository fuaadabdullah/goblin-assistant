import { runtimeClient } from '../index';

type MockFetchResponse = {
  ok: boolean;
  status?: number;
  json: () => Promise<unknown>;
};

describe('runtimeClient model registry integration', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    jest.restoreAllMocks();
  });

  it('derives providers from /api/models and normalizes ids', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        providers: [
          { id: 'openai' },
          { id: 'azure-openai' },
        ],
        models: [
          { provider: 'openai', name: 'gpt-4o-mini' },
          { provider: 'openai', name: 'gpt-4o-mini' },
          { provider: 'azure-openai', name: 'gpt-4o' },
        ],
      }),
    } as MockFetchResponse);
    global.fetch = fetchMock as unknown as typeof fetch;

    const providers = await runtimeClient.getProviders();

    expect(providers).toEqual(['openai', 'azure_openai']);
    expect(fetchMock).toHaveBeenCalledWith('/api/models', { method: 'GET' });
  });

  it('derives provider-scoped models from /api/models', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        models: [
          {
            provider: 'openai',
            name: 'gpt-4o-mini',
            is_selectable: true,
            health: 'healthy',
          },
          {
            provider: 'openai',
            name: 'gpt-4o',
            is_selectable: false,
            health: 'unhealthy',
            health_reason: 'Provider health check failed.',
          },
          { provider: 'openai', name: 'gpt-4o-mini' },
          { provider: 'ollama_gcp', name: 'qwen2.5:3b' },
        ],
      }),
    } as MockFetchResponse);
    global.fetch = fetchMock as unknown as typeof fetch;

    const openAiModels = await runtimeClient.getProviderModels('openai');
    const ollamaModels = await runtimeClient.getProviderModels('ollama-gcp');
    const openAiOptions = await runtimeClient.getProviderModelOptions('openai');

    expect(openAiModels).toEqual(['gpt-4o-mini']);
    expect(ollamaModels).toEqual(['qwen2.5:3b']);
    expect(openAiOptions).toEqual([
      {
        name: 'gpt-4o',
        provider: 'openai',
        health: 'unhealthy',
        isSelectable: false,
        healthReason: 'Provider health check failed.',
      },
      {
        name: 'gpt-4o-mini',
        provider: 'openai',
        health: 'healthy',
        isSelectable: true,
        healthReason: null,
      },
    ]);
  });

  it('returns empty providers/models when registry request fails', async () => {
    const fetchMock = jest.fn().mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => ({ error: 'Backend unreachable' }),
    } as MockFetchResponse);
    global.fetch = fetchMock as unknown as typeof fetch;

    await expect(runtimeClient.getProviders()).resolves.toEqual([]);
    await expect(runtimeClient.getProviderModels('openai')).resolves.toEqual([]);
  });
});
