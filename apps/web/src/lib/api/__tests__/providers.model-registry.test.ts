/**
 * Tests for the model-registry methods added to providersMethods / apiClient.
 * These replace the old runtimeClient tests in src/api/__tests__/runtimeClient.test.ts
 * and point at the canonical apiClient instead.
 */

import { apiClient } from '../index';

type MockFetchResponse = {
  ok: boolean;
  status?: number;
  json: () => Promise<unknown>;
};

// frontendHttp (axios) is used under getFrontend — mock the underlying fetch
// that axios calls, or mock axios itself. We mock at the axios level.
jest.mock('axios', () => {
  const actual = jest.requireActual('axios');
  return {
    ...actual,
    create: jest.fn(() => ({
      get: jest.fn(),
      post: jest.fn(),
      put: jest.fn(),
      patch: jest.fn(),
      delete: jest.fn(),
      interceptors: {
        request: { use: jest.fn(), eject: jest.fn() },
        response: { use: jest.fn(), eject: jest.fn() },
      },
    })),
    isAxiosError: actual.isAxiosError,
  };
});

// Instead of fighting axios mocks we mock getFrontend/getBackend at the module level.
jest.mock('../shared', () => {
  const actual = jest.requireActual('../shared');
  return {
    ...actual,
    getFrontend: jest.fn(),
    getBackend: jest.fn(),
    postBackend: jest.fn(),
    putBackend: jest.fn(),
    patchBackend: jest.fn(),
  };
});

import { getFrontend, getBackend } from '../shared';

const mockGetFrontend = getFrontend as jest.MockedFunction<typeof getFrontend>;
const mockGetBackend = getBackend as jest.MockedFunction<typeof getBackend>;

const registryWithProviders = {
  providers: [{ id: 'openai' }, { id: 'azure-openai' }],
  models: [
    { provider: 'openai', name: 'gpt-4o-mini', is_selectable: true, health: 'healthy' },
    { provider: 'openai', name: 'gpt-4o-mini' }, // duplicate — should merge
    { provider: 'azure-openai', name: 'gpt-4o', is_selectable: true, health: 'healthy' },
  ],
};

const registryWithModelsOnly = {
  models: [
    { provider: 'openai', name: 'gpt-4o-mini', is_selectable: true, health: 'healthy' },
    {
      provider: 'openai',
      name: 'gpt-4o',
      is_selectable: false,
      health: 'unhealthy',
      health_reason: 'Provider health check failed.',
    },
    { provider: 'openai', name: 'gpt-4o-mini' }, // duplicate
    { provider: 'ollama_gcp', name: 'qwen2.5:3b', is_selectable: true, health: 'healthy' },
  ],
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('apiClient.getProviders', () => {
  it('derives providers from the providers list and normalizes ids', async () => {
    mockGetFrontend.mockResolvedValue(registryWithProviders);

    const providers = await apiClient.getProviders();

    expect(providers).toEqual(['openai', 'azure_openai']);
  });

  it('falls back to deriving providers from models when providers list is empty', async () => {
    mockGetFrontend.mockResolvedValue({ providers: [], models: registryWithModelsOnly.models });

    const providers = await apiClient.getProviders();

    expect(providers).toContain('openai');
    expect(providers).toContain('ollama_gcp');
    expect(new Set(providers).size).toBe(providers.length); // no duplicates
  });

  it('returns empty array when registry fetch fails', async () => {
    mockGetFrontend.mockRejectedValue(new Error('Network error'));

    await expect(apiClient.getProviders()).resolves.toEqual([]);
  });
});

describe('apiClient.getProviderModelOptions', () => {
  it('returns options for a specific provider', async () => {
    mockGetFrontend.mockResolvedValue(registryWithModelsOnly);

    const options = await apiClient.getProviderModelOptions('openai');

    // Should be sorted alphabetically
    expect(options[0].name).toBe('gpt-4o');
    expect(options[1].name).toBe('gpt-4o-mini');
  });

  it('merges duplicate entries and upgrades selectability', async () => {
    // gpt-4o-mini appears twice: once without is_selectable (defaults to true)
    // and once with is_selectable: true — merged result should be selectable
    mockGetFrontend.mockResolvedValue(registryWithModelsOnly);

    const options = await apiClient.getProviderModelOptions('openai');
    const mini = options.find((o) => o.name === 'gpt-4o-mini');

    expect(mini?.isSelectable).toBe(true);
    expect(mini?.health).toBe('healthy');
  });

  it('preserves healthReason for non-selectable models', async () => {
    mockGetFrontend.mockResolvedValue(registryWithModelsOnly);

    const options = await apiClient.getProviderModelOptions('openai');
    const gpt4o = options.find((o) => o.name === 'gpt-4o');

    expect(gpt4o?.isSelectable).toBe(false);
    expect(gpt4o?.healthReason).toBe('Provider health check failed.');
  });

  it('normalizes hyphenated provider id (ollama-gcp → ollama_gcp)', async () => {
    mockGetFrontend.mockResolvedValue(registryWithModelsOnly);

    const options = await apiClient.getProviderModelOptions('ollama-gcp');

    expect(options).toHaveLength(1);
    expect(options[0].name).toBe('qwen2.5:3b');
  });

  it('returns empty array for unknown provider', async () => {
    mockGetFrontend.mockResolvedValue(registryWithProviders);

    await expect(apiClient.getProviderModelOptions('unknown-provider')).resolves.toEqual([]);
  });

  it('returns empty array when registry fetch fails', async () => {
    mockGetFrontend.mockRejectedValue(new Error('502 Bad Gateway'));

    await expect(apiClient.getProviderModelOptions('openai')).resolves.toEqual([]);
  });
});

describe('apiClient.getProviderModels', () => {
  it('returns only selectable model names', async () => {
    mockGetFrontend.mockResolvedValue(registryWithModelsOnly);

    const models = await apiClient.getProviderModels('openai');

    expect(models).toContain('gpt-4o-mini');
    expect(models).not.toContain('gpt-4o'); // is_selectable: false
  });

  it('returns selectable models for ollama-gcp via alias', async () => {
    mockGetFrontend.mockResolvedValue(registryWithModelsOnly);

    const models = await apiClient.getProviderModels('ollama-gcp');

    expect(models).toEqual(['qwen2.5:3b']);
  });

  it('returns empty when registry fetch fails', async () => {
    mockGetFrontend.mockRejectedValue(new Error('timeout'));

    await expect(apiClient.getProviderModels('openai')).resolves.toEqual([]);
  });
});

describe('apiClient.getCostSummary', () => {
  it('returns cost summary from backend', async () => {
    const summary = {
      total_cost: 1.23,
      cost_by_provider: { openai: 1.0, anthropic: 0.23 },
      cost_by_model: {},
      requests_by_provider: { openai: 10 },
    };
    mockGetBackend.mockResolvedValue(summary);

    const result = await apiClient.getCostSummary();

    expect(result.total_cost).toBe(1.23);
    expect(result.cost_by_provider.openai).toBe(1.0);
    expect(mockGetBackend).toHaveBeenCalledWith('/costs/summary');
  });

  it('returns empty cost summary when backend call fails', async () => {
    mockGetBackend.mockRejectedValue(new Error('503'));

    const result = await apiClient.getCostSummary();

    expect(result.total_cost).toBe(0);
    expect(result.cost_by_provider).toEqual({});
  });
});
