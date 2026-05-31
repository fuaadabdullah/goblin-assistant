/**
 * runtimeClient adapter tests.
 *
 * Model-registry logic (getProviders, getProviderModelOptions, getProviderModels)
 * has moved to apiClient — see src/lib/api/__tests__/providers.model-registry.test.ts
 * for the authoritative tests of that logic.
 *
 * These tests verify that the runtimeClient adapter correctly delegates to
 * apiClient and providerKeys.
 */

import { runtimeClient, apiClient } from '@/api';

jest.mock('@/lib/api', () => ({
  apiClient: {
    getProviders: jest.fn(),
    getProviderModelOptions: jest.fn(),
    getProviderModels: jest.fn(),
    getCostSummary: jest.fn(),
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
    validateToken: jest.fn(),
  },
  getBackend: jest.fn(),
  postBackend: jest.fn(),
  putBackend: jest.fn(),
  patchBackend: jest.fn(),
}));

jest.mock('@/lib/provider-keys', () => ({
  providerKeys: {
    get: jest.fn(),
    set: jest.fn(),
    remove: jest.fn(),
  },
}));

import { providerKeys } from '@/lib/provider-keys';

const mockGetProviders = apiClient.getProviders as jest.MockedFunction<
  typeof apiClient.getProviders
>;
const mockGetProviderModelOptions = apiClient.getProviderModelOptions as jest.MockedFunction<
  typeof apiClient.getProviderModelOptions
>;
const mockGetCostSummary = apiClient.getCostSummary as jest.MockedFunction<
  typeof apiClient.getCostSummary
>;
const mockLogin = apiClient.login as jest.MockedFunction<typeof apiClient.login>;
const mockLogout = apiClient.logout as jest.MockedFunction<typeof apiClient.logout>;
const mockPKGet = providerKeys.get as jest.MockedFunction<typeof providerKeys.get>;
const mockPKSet = providerKeys.set as jest.MockedFunction<typeof providerKeys.set>;
const mockPKRemove = providerKeys.remove as jest.MockedFunction<typeof providerKeys.remove>;

beforeEach(() => {
  jest.clearAllMocks();
});

describe('runtimeClient model-registry delegation', () => {
  it('delegates getProviders to apiClient', async () => {
    mockGetProviders.mockResolvedValue(['openai', 'anthropic']);

    const result = await runtimeClient.getProviders();

    expect(result).toEqual(['openai', 'anthropic']);
    expect(mockGetProviders).toHaveBeenCalledTimes(1);
  });

  it('delegates getProviderModelOptions to apiClient', async () => {
    const opts = [{ name: 'gpt-4o', provider: 'openai', isSelectable: true, healthReason: null }];
    mockGetProviderModelOptions.mockResolvedValue(opts);

    const result = await runtimeClient.getProviderModelOptions('openai');

    expect(result).toEqual(opts);
    expect(mockGetProviderModelOptions).toHaveBeenCalledWith('openai');
  });

  it('delegates getCostSummary to apiClient', async () => {
    const summary = {
      total_cost: 5.5,
      cost_by_provider: { openai: 5.5 },
      cost_by_model: {},
      requests_by_provider: {},
    };
    mockGetCostSummary.mockResolvedValue(summary);

    const result = await runtimeClient.getCostSummary();

    expect(result.total_cost).toBe(5.5);
  });
});

describe('runtimeClient provider API key management', () => {
  it('delegates setProviderApiKey to providerKeys.set', async () => {
    await runtimeClient.setProviderApiKey('openai', 'sk-test-key');
    expect(mockPKSet).toHaveBeenCalledWith('openai', 'sk-test-key');
  });

  it('delegates storeApiKey to providerKeys.set', async () => {
    await runtimeClient.storeApiKey('anthropic', 'ant-key');
    expect(mockPKSet).toHaveBeenCalledWith('anthropic', 'ant-key');
  });

  it('delegates getApiKey to providerKeys.get', async () => {
    mockPKGet.mockReturnValue('sk-stored');
    const key = await runtimeClient.getApiKey('openai');
    expect(key).toBe('sk-stored');
    expect(mockPKGet).toHaveBeenCalledWith('openai');
  });

  it('delegates clearApiKey to providerKeys.remove', async () => {
    await runtimeClient.clearApiKey('openai');
    expect(mockPKRemove).toHaveBeenCalledWith('openai');
  });
});

describe('runtimeClient auth delegation', () => {
  it('delegates login to apiClient', async () => {
    const loginResponse = { access_token: 'jwt', user: { id: 'u1' } } as any;
    mockLogin.mockResolvedValue(loginResponse);

    const result = await runtimeClient.login('user@example.com', 'pass');

    expect(result).toEqual(loginResponse);
    expect(mockLogin).toHaveBeenCalledWith('user@example.com', 'pass');
  });

  it('delegates logout to apiClient (best-effort, never throws)', async () => {
    mockLogout.mockRejectedValue(new Error('network error'));

    await expect(runtimeClient.logout()).resolves.toBeUndefined();
  });
});

describe('runtimeClient stub methods', () => {
  it('getGoblins returns empty array', async () => {
    await expect(runtimeClient.getGoblins()).resolves.toEqual([]);
  });

  it('executeTask returns stub message', async () => {
    const result = await runtimeClient.executeTask('goblin', 'task');
    expect(typeof result).toBe('string');
    expect(result.length).toBeGreaterThan(0);
  });

  it('executeTaskStreaming calls onChunk then onComplete', async () => {
    const onChunk = jest.fn();
    const onComplete = jest.fn();

    await runtimeClient.executeTaskStreaming('goblin', 'task', onChunk, onComplete);

    expect(onChunk).toHaveBeenCalledWith(expect.objectContaining({ done: true }));
    expect(onComplete).toHaveBeenCalled();
  });

  it('parseOrchestration returns empty plan', async () => {
    const plan = await runtimeClient.parseOrchestration('task1 THEN task2');
    expect(plan.steps).toEqual([]);
    expect(typeof plan.total_batches).toBe('number');
  });
});
