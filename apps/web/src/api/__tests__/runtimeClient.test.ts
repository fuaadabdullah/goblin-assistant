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

import { runtimeClient } from '@/lib/api/runtimeClient';
import { apiClient } from '@/lib/api';
import { TextDecoder } from 'util';
import type { LoginResponse } from '@/types/api';

jest.mock('@/lib/api', () => ({
  apiClient: {
    getGoblins: jest.fn(),
    getProviders: jest.fn(),
    getProviderModelOptions: jest.fn(),
    getProviderModels: jest.fn(),
    getHistory: jest.fn(),
    getStats: jest.fn(),
    parseOrchestration: jest.fn(),
    createConversation: jest.fn(),
    sendConversationMessage: jest.fn(),
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
const mockGetGoblins = apiClient.getGoblins as jest.MockedFunction<typeof apiClient.getGoblins>;
const mockGetHistory = apiClient.getHistory as jest.MockedFunction<typeof apiClient.getHistory>;
const mockGetStats = apiClient.getStats as jest.MockedFunction<typeof apiClient.getStats>;
const mockParseOrchestration = apiClient.parseOrchestration as jest.MockedFunction<
  typeof apiClient.parseOrchestration
>;
const mockCreateConversation = apiClient.createConversation as jest.MockedFunction<
  typeof apiClient.createConversation
>;
const mockSendConversationMessage = apiClient.sendConversationMessage as jest.MockedFunction<
  typeof apiClient.sendConversationMessage
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
  (globalThis as typeof globalThis & { fetch: jest.Mock }).fetch = jest.fn();
  (globalThis as typeof globalThis & { TextDecoder: typeof TextDecoder }).TextDecoder = TextDecoder;
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
    const loginResponse = { access_token: 'jwt', user: { id: 'u1' } } as unknown as LoginResponse;
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

describe('runtimeClient runtime delegation', () => {
  it('delegates getGoblins to apiClient', async () => {
    mockGetGoblins.mockResolvedValue([{ id: 'demo', name: 'demo', title: 'Demo', status: 'ok' }]);
    await expect(runtimeClient.getGoblins()).resolves.toHaveLength(1);
    expect(mockGetGoblins).toHaveBeenCalledTimes(1);
  });

  it('delegates getHistory/getStats/parseOrchestration to apiClient', async () => {
    mockGetHistory.mockResolvedValue([
      { id: 'h1', goblin: 'demo', task: 't', response: 'r', timestamp: 1 },
    ]);
    mockGetStats.mockResolvedValue({ total_tasks: 1 });
    mockParseOrchestration.mockResolvedValue({ steps: [], total_batches: 0, max_parallel: 0 });

    await expect(runtimeClient.getHistory('demo', 5)).resolves.toHaveLength(1);
    await expect(runtimeClient.getStats('demo')).resolves.toEqual({ total_tasks: 1 });
    await expect(runtimeClient.parseOrchestration('a THEN b', 'demo')).resolves.toEqual({
      steps: [],
      total_batches: 0,
      max_parallel: 0,
    });
    expect(mockGetHistory).toHaveBeenCalledWith('demo', 5);
    expect(mockGetStats).toHaveBeenCalledWith('demo');
    expect(mockParseOrchestration).toHaveBeenCalledWith('a THEN b', 'demo');
  });

  it('executeTask sends message through chat-router conversation flow', async () => {
    mockCreateConversation.mockResolvedValue({
      conversationId: 'conv-1',
      title: 'Runtime Task Execution',
      createdAt: '2026-01-01T00:00:00Z',
    });
    mockSendConversationMessage.mockResolvedValue({
      messageId: 'm1',
      content: 'runtime result',
      provider: 'openai',
      model: 'gpt-4o-mini',
      createdAt: '2026-01-01T00:00:01Z',
    });

    const result = await runtimeClient.executeTask('docs-writer', 'do thing');

    expect(result).toBe('runtime result');
    expect(mockCreateConversation).toHaveBeenCalledTimes(1);
    expect(mockSendConversationMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        conversationId: 'conv-1',
      })
    );
  });

  it('executeTaskStreaming emits chunks and completion', async () => {
    mockCreateConversation.mockResolvedValue({
      conversationId: 'conv-stream',
      title: 'Runtime Task Execution',
      createdAt: '2026-01-01T00:00:00Z',
    });

    const chunks = [
      Buffer.from('data: {"content":"hello ","token_count":2,"cost_delta":0.001,"done":false}\n\n'),
      Buffer.from(
        'data: {"result":"hello world","message_id":"m1","provider":"openai","model":"gpt-4o-mini","tokens":5,"cost":0.002,"duration_ms":100,"done":true}\n\n'
      ),
    ];
    let idx = 0;
    const stream = {
      getReader: () => ({
        read: async () => {
          if (idx >= chunks.length) return { done: true, value: undefined };
          const value = new Uint8Array(chunks[idx]);
          idx += 1;
          return { done: false, value };
        },
        cancel: async () => undefined,
      }),
    };

    (globalThis as typeof globalThis & { fetch: jest.Mock }).fetch.mockResolvedValue({
      ok: true,
      body: stream,
      status: 200,
    });

    const onChunk = jest.fn();
    const onComplete = jest.fn();

    await runtimeClient.executeTaskStreaming('goblin', 'task', onChunk, onComplete);

    expect(onChunk).toHaveBeenCalledWith(expect.objectContaining({ content: 'hello ' }));
    expect(onComplete).toHaveBeenCalledWith(expect.objectContaining({ done: true }));
  });
});
