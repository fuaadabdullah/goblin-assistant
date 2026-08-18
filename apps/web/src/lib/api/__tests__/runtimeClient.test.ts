import { beforeEach, describe, expect, it, vi } from 'vitest';

const {
  mockApiClient,
  mockCreateConversation,
  mockSendConversationMessage,
  mockChatCompletion,
  mockStreamRuntimeTask,
  mockPKGet,
  mockPKSet,
  mockPKRemove,
} = vi.hoisted(() => {
  const mockCreateConversation = vi.fn();
  const mockSendConversationMessage = vi.fn();
  const mockChatCompletion = vi.fn();
  const mockStreamRuntimeTask = vi.fn();
  const mockPKGet = vi.fn();
  const mockPKSet = vi.fn();
  const mockPKRemove = vi.fn();

  const mockApiClient = {
    createConversation: mockCreateConversation,
    sendConversationMessage: mockSendConversationMessage,
    chatCompletion: mockChatCompletion,
    getGoblins: vi.fn(),
    getProviders: vi.fn(),
    getProviderModelOptions: vi.fn(),
    getProviderModels: vi.fn(),
    getHistory: vi.fn(),
    getStats: vi.fn(),
    getCostSummary: vi.fn(),
    parseOrchestration: vi.fn(),
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    validateToken: vi.fn(),
  };

  return {
    mockApiClient,
    mockCreateConversation,
    mockSendConversationMessage,
    mockChatCompletion,
    mockStreamRuntimeTask,
    mockPKGet,
    mockPKSet,
    mockPKRemove,
  };
});

vi.mock('@/lib/api', () => ({
  apiClient: mockApiClient,
}));

vi.mock('@/api/runtime-stream', () => ({
  streamRuntimeTask: mockStreamRuntimeTask,
}));

vi.mock('@/lib/provider-keys', () => ({
  providerKeys: {
    set: mockPKSet,
    get: mockPKGet,
    remove: mockPKRemove,
  },
}));

let runtimeClient: any;

describe('runtimeClient', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    mockCreateConversation.mockResolvedValue({
      conversationId: 'conv-runtime',
      title: 'Runtime Task Execution',
      createdAt: '2026-01-01T00:00:00.000Z',
    });
    vi.resetModules();
    runtimeClient = (await import('../runtimeClient')).runtimeClient;
  });

  it('falls back to chatCompletion when provider access is denied', async () => {
    mockSendConversationMessage.mockRejectedValueOnce({
      response: {
        status: 200,
        data: { error: 'provider-access-denied' },
      },
    });
    mockChatCompletion.mockResolvedValueOnce('runtime fallback reply');

    const result = await runtimeClient.executeTask(
      'docs',
      'Summarize the latest notes',
      false,
      'code context',
      'openai',
      'gpt-4o-mini'
    );

    expect(mockCreateConversation).toHaveBeenCalledWith('Runtime Task Execution');
    expect(mockSendConversationMessage).toHaveBeenCalledWith({
      conversationId: 'conv-runtime',
      message: expect.stringContaining('[goblin:docs]'),
      provider: 'openai',
      model: 'gpt-4o-mini',
      metadata: { source: 'runtime-client', goblin: 'docs' },
    });
    expect(mockChatCompletion).toHaveBeenCalledWith(
      [{ role: 'user', content: expect.stringContaining('[goblin:docs]') }],
      'gpt-4o-mini'
    );
    expect(result).toBe('runtime fallback reply');
  });

  it('delegates the remaining runtime methods to the shared client helpers', async () => {
    mockSendConversationMessage.mockResolvedValueOnce({ content: 'runtime reply' });
    mockApiClient.getGoblins.mockResolvedValue([
      { id: 'g1', name: 'g1', title: 'G1', status: 'active', active: true },
    ]);
    mockApiClient.getProviders.mockResolvedValue(['openai']);
    mockApiClient.getProviderModelOptions.mockResolvedValue([{ id: 'm1' }]);
    mockApiClient.getProviderModels.mockResolvedValue(['gpt-4o-mini']);
    mockApiClient.getHistory.mockResolvedValue([
      {
        id: 'memory-1',
        goblin_id: 'docs',
        task: 'task',
        response: 'response',
        timestamp: '2026-08-03T00:00:00Z',
      },
    ]);
    mockApiClient.getStats.mockResolvedValue({
      goblin_id: 'docs',
      window: {
        hours: 24,
        started_at: '2026-08-02T00:00:00Z',
        ended_at: '2026-08-03T00:00:00Z',
      },
      counters: {
        total_tasks: 1,
        completed_tasks: 1,
        failed_tasks: 0,
      },
      latency: {
        average_duration_ms: null,
        p95_duration_ms: null,
      },
      success_rate: 1,
      total_cost: null,
    });
    mockApiClient.getCostSummary.mockResolvedValue({ total_cost_usd: 1.23 });
    mockApiClient.parseOrchestration.mockResolvedValue({ plan: [] });
    mockApiClient.login.mockResolvedValue({ access_token: 'tok' });
    mockApiClient.register.mockResolvedValue({ access_token: 'tok' });
    mockApiClient.logout.mockResolvedValue(undefined);
    mockApiClient.validateToken.mockResolvedValue({ valid: true, user: { id: 'user-1' } });

    await expect(
      runtimeClient.executeTask(
        'docs',
        'Write the summary',
        false,
        'code context',
        'openai',
        'gpt-4o-mini'
      )
    ).resolves.toBe('runtime reply');

    await expect(runtimeClient.getGoblins()).resolves.toEqual([
      { id: 'g1', name: 'g1', title: 'G1', status: 'active', active: true },
    ]);
    await expect(runtimeClient.getProviders()).resolves.toEqual(['openai']);
    await expect(runtimeClient.getProviderModelOptions('openai')).resolves.toEqual([{ id: 'm1' }]);
    await expect(runtimeClient.getProviderModels('openai')).resolves.toEqual(['gpt-4o-mini']);

    await expect(runtimeClient.executeTaskStreaming('docs', 'Stream this', vi.fn())).resolves.toBe(
      undefined
    );
    expect(mockStreamRuntimeTask).toHaveBeenCalledWith(
      {
        conversationId: 'conv-runtime',
        prompt: expect.stringContaining('[goblin:docs]'),
        provider: undefined,
        model: undefined,
        goblin: 'docs',
      },
      {
        onChunk: expect.any(Function),
        onComplete: undefined,
      }
    );

    await runtimeClient.setProviderApiKey('openai', 'key-1');
    await runtimeClient.storeApiKey('openai', 'key-2');
    await runtimeClient.clearApiKey('openai');
    expect(mockPKSet).toHaveBeenCalledWith('openai', 'key-1');
    expect(mockPKSet).toHaveBeenCalledWith('openai', 'key-2');
    expect(mockPKRemove).toHaveBeenCalledWith('openai');

    await expect(runtimeClient.getHistory('docs', 5)).resolves.toEqual([
      {
        id: 'memory-1',
        goblin_id: 'docs',
        task: 'task',
        response: 'response',
        timestamp: '2026-08-03T00:00:00Z',
      },
    ]);
    await expect(runtimeClient.getStats('docs')).resolves.toMatchObject({
      counters: { total_tasks: 1 },
    });
    await expect(runtimeClient.getCostSummary()).resolves.toEqual({ total_cost_usd: 1.23 });
    await expect(runtimeClient.parseOrchestration('plan this', 'docs')).resolves.toEqual({
      plan: [],
    });
    mockPKGet.mockReturnValue('stored-key');
    await expect(runtimeClient.getApiKey('openai')).resolves.toBe('stored-key');
    expect(mockPKGet).toHaveBeenCalledWith('openai');

    await expect(runtimeClient.login('user@example.com', 'secret')).resolves.toEqual({
      access_token: 'tok',
    });
    await expect(runtimeClient.register('user@example.com', 'secret')).resolves.toEqual({
      access_token: 'tok',
    });
    await expect(runtimeClient.logout()).resolves.toBeUndefined();
    await expect(runtimeClient.validateToken('jwt-token')).resolves.toEqual({
      valid: true,
      user: { id: 'user-1' },
    });
  });
});
