import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockCreateConversation, mockSendConversationMessage, mockChatCompletion } = vi.hoisted(
  () => ({
    mockCreateConversation: vi.fn(),
    mockSendConversationMessage: vi.fn(),
    mockChatCompletion: vi.fn(),
  })
);

vi.mock('@/lib/api', () => ({
  apiClient: {
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
  },
  V1_CHAT_PREFIX: '/api/v1/chat',
}));

vi.mock('@/api/runtime-stream', () => ({
  streamRuntimeTask: vi.fn(),
}));

vi.mock('@/lib/provider-keys', () => ({
  providerKeys: {
    set: vi.fn(),
    get: vi.fn(),
    remove: vi.fn(),
  },
}));

import { runtimeClient } from '../runtimeClient';

describe('runtimeClient', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCreateConversation.mockResolvedValue({
      conversationId: 'conv-runtime',
      title: 'Runtime Task Execution',
      createdAt: '2026-01-01T00:00:00.000Z',
    });
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
});
