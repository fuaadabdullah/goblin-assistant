import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { renderHook, act, waitFor } from '@testing-library/react';
import type { ChatThread } from '../../types';

const setQueryDataMock = jest.fn();
let backendConversationData: {
  conversationId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: Array<Record<string, unknown>>;
} | undefined;

jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn(({ enabled, queryFn }: { enabled?: boolean; queryFn?: () => Promise<unknown> }) => {
    if (enabled && typeof queryFn === 'function') {
      void queryFn();
    }
    return {
      data: backendConversationData,
      isLoading: false,
      isFetching: false,
    };
  }),
  useQueryClient: jest.fn(() => ({
    setQueryData: setQueryDataMock,
  })),
}));

jest.mock('../../api', () => ({
  chatClient: {
    createConversation: jest.fn(),
    listConversations: jest.fn(),
    getConversation: jest.fn(),
    sendMessage: jest.fn(),
    importConversationMessages: jest.fn(),
  },
}));

jest.mock('../../../../lib/ui-error', () => ({
  toUiError: jest.fn(() => ({
    code: 'CHAT_SEND_FAILED',
    userMessage: 'Sorry, we could not send that message right now.',
  })),
}));

jest.mock('../../../../lib/chat-history', () => ({
  buildThreadKey: jest.requireActual('../../../../lib/chat-history').buildThreadKey,
  readChatThreads: jest.fn(() => []),
  readChatMessages: jest.fn(() => []),
  removeChatMessages: jest.fn(),
  removeChatThread: jest.fn(),
  sortChatThreads: jest.requireActual('../../../../lib/chat-history').sortChatThreads,
  writeChatThreads: jest.fn(),
}));

jest.mock('../../../../lib/cost-estimate', () => ({
  estimateFromText: jest.fn((text: string) => ({
    estimated_tokens: text?.trim() ? 42 : 0,
    estimated_cost_usd: text?.trim() ? 0.0042 : 0,
  })),
}));

jest.mock('../../../../lib/llm-rates', () => ({
  computeCostUsd: jest.fn(() => ({
    cost_usd: 0.001,
    approx: true,
    source: 'estimate',
  })),
}));

const upsertThreadMock = jest.fn();
const removeThreadMock = jest.fn();
const invalidateThreadsMock = jest.fn();
const useChatThreadsMock = jest.fn();
let currentThreads: ChatThread[] = [];

jest.mock('../useChatThreads', () => ({
  useChatThreads: () => useChatThreadsMock(),
}));

jest.mock('../../../../contexts/ProviderContext', () => ({
  useProvider: jest.fn(() => ({
    selectedProvider: 'openai',
    selectedModel: 'gpt-4o-mini',
  })),
}));

jest.mock('../../../../utils/auth-session', () => ({
  getAuthToken: jest.fn(() => 'mock-auth-token'),
}));

const { useChatSession } = require('../useChatSession') as typeof import('../useChatSession');
const { chatClient } = require('../../api') as typeof import('../../api');
const { buildThreadKey, readChatMessages } = require('../../../../lib/chat-history') as typeof import('../../../../lib/chat-history');
const { toUiError } = require('../../../../lib/ui-error') as typeof import('../../../../lib/ui-error');

const legacyThread: ChatThread = {
  id: 'legacy-1',
  source: 'legacy-local',
  threadKey: buildThreadKey('legacy-local', 'legacy-1'),
  title: 'Legacy thread',
  snippet: 'Saved locally',
  createdAt: '2026-02-20T00:00:00.000Z',
  updatedAt: '2026-02-20T00:00:00.000Z',
};

const backendThread: ChatThread = {
  id: 'conv-123',
  source: 'backend',
  threadKey: buildThreadKey('backend', 'conv-123'),
  title: 'Backend thread',
  snippet: 'Persisted remotely',
  createdAt: '2026-02-21T00:00:00.000Z',
  updatedAt: '2026-02-21T00:00:00.000Z',
};

describe('useChatSession', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    backendConversationData = undefined;
    currentThreads = [];
    upsertThreadMock.mockReset();
    removeThreadMock.mockReset();
    invalidateThreadsMock.mockReset();
    upsertThreadMock.mockImplementation(input => {
      const source = input.source ?? 'backend';
      const nextThread: ChatThread = {
        id: input.id,
        source,
        threadKey: buildThreadKey(source, input.id),
        title: input.title ?? 'Untitled chat',
        snippet: input.snippet ?? '',
        createdAt: input.createdAt ?? new Date().toISOString(),
        updatedAt: input.updatedAt ?? new Date().toISOString(),
      };
      currentThreads = [
        nextThread,
        ...currentThreads.filter(thread => thread.threadKey !== nextThread.threadKey),
      ];
    });
    removeThreadMock.mockImplementation(thread => {
      currentThreads = currentThreads.filter(item => item.threadKey !== thread.threadKey);
    });
    useChatThreadsMock.mockImplementation(() => ({
      threads: currentThreads,
      isLoading: false,
      upsertThread: upsertThreadMock,
      removeThread: removeThreadMock,
      invalidateThreads: invalidateThreadsMock,
    }));
  });

  it('initializes with expected default state', () => {
    const { result } = renderHook(() => useChatSession());

    expect(result.current.messages).toEqual([]);
    expect(result.current.input).toBe('');
    expect(result.current.isSending).toBe(false);
    expect(result.current.isMessagesLoading).toBe(false);
    expect(result.current.totalTokens).toBe(0);
    expect(result.current.totalCostUsd).toBe(0);
    expect(result.current.quickPrompts.length).toBeGreaterThan(0);
  });

  it('creates a backend thread, sends a message, and updates totals', async () => {
    (chatClient.createConversation as jest.Mock).mockResolvedValue({
      conversationId: 'conv-123',
      title: 'Test message',
      createdAt: '2026-02-21T00:00:00.000Z',
    });
    (chatClient.sendMessage as jest.Mock).mockResolvedValue({
      messageId: 'assistant-1',
      content: 'Assistant response',
      provider: 'openai',
      model: 'gpt-4o-mini',
      createdAt: '2026-02-21T00:00:01.000Z',
      usage: { input_tokens: 10, output_tokens: 20, total_tokens: 30 },
      cost_usd: 0.0025,
    });
    (chatClient.getConversation as jest.Mock).mockResolvedValue({
      conversationId: 'conv-123',
      title: 'Test message',
      createdAt: '2026-02-21T00:00:00.000Z',
      updatedAt: '2026-02-21T00:00:01.000Z',
      messages: [
        {
          id: 'user-1',
          createdAt: '2026-02-21T00:00:00.000Z',
          role: 'user',
          content: 'Test message',
        },
        {
          id: 'assistant-1',
          createdAt: '2026-02-21T00:00:01.000Z',
          role: 'assistant',
          content: 'Assistant response',
          meta: {
            usage: { input_tokens: 10, output_tokens: 20, total_tokens: 30 },
            cost_usd: 0.0025,
          },
        },
      ],
    });

    const { result } = renderHook(() => useChatSession());

    act(() => {
      result.current.setInput('Test message');
    });

    await act(async () => {
      await result.current.sendMessage();
    });

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2);
    });

    expect(chatClient.createConversation).toHaveBeenCalledWith({
      title: 'Test message',
    });
    expect(chatClient.sendMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        conversationId: 'conv-123',
        prompt: 'Test message',
        provider: 'openai',
        model: 'gpt-4o-mini',
      }),
    );
    expect(upsertThreadMock).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'conv-123',
        source: 'backend',
      }),
    );
    expect(result.current.activeThreadKey).toBe(buildThreadKey('backend', 'conv-123'));
    expect(result.current.totalTokens).toBe(30);
    expect(result.current.totalCostUsd).toBe(0.0025);
  });

  it('hydrates backend conversation history when a backend thread is selected', async () => {
    currentThreads = [backendThread];
    backendConversationData = {
      conversationId: 'conv-123',
      title: 'Backend thread',
      createdAt: '2026-02-21T00:00:00.000Z',
      updatedAt: '2026-02-21T00:00:01.000Z',
      messages: [
        {
          id: 'm1',
          createdAt: '2026-02-21T00:00:00.000Z',
          role: 'assistant',
          content: 'Persisted',
          meta: { usage: { total_tokens: 12 }, cost_usd: 0.0012 },
        },
      ],
    };

    const { result } = renderHook(() => useChatSession());

    await waitFor(() => {
      expect(chatClient.getConversation).toHaveBeenCalledWith('conv-123');
    });

    expect(result.current.messages[0].content).toBe('Persisted');
    expect(result.current.totalTokens).toBe(12);
    expect(result.current.totalCostUsd).toBe(0.0012);
  });

  it('promotes a legacy thread on send and removes the local copy after success', async () => {
    currentThreads = [legacyThread];
    (readChatMessages as jest.Mock).mockReturnValue([
      {
        id: 'legacy-msg-1',
        createdAt: '2026-02-20T00:00:00.000Z',
        role: 'user',
        content: 'Old local question',
      },
    ]);
    (chatClient.createConversation as jest.Mock).mockResolvedValue({
      conversationId: 'conv-promoted',
      title: 'Legacy thread',
      createdAt: '2026-02-21T00:00:00.000Z',
    });
    (chatClient.importConversationMessages as jest.Mock).mockResolvedValue(undefined);
    (chatClient.sendMessage as jest.Mock).mockResolvedValue({
      messageId: 'assistant-promoted',
      content: 'Promoted response',
      provider: 'openai',
      model: 'gpt-4o-mini',
      createdAt: '2026-02-21T00:00:02.000Z',
      usage: { total_tokens: 24 },
      cost_usd: 0.003,
    });

    const { result } = renderHook(() => useChatSession());

    await waitFor(() => {
      expect(result.current.activeThreadKey).toBe(legacyThread.threadKey);
    });

    act(() => {
      result.current.setInput('Continue this thread');
    });

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(chatClient.createConversation).toHaveBeenCalledWith({
      title: 'Legacy thread',
    });
    expect(chatClient.importConversationMessages).toHaveBeenCalledWith(
      'conv-promoted',
      expect.arrayContaining([
        expect.objectContaining({ content: 'Old local question' }),
      ]),
    );
    expect(chatClient.sendMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        conversationId: 'conv-promoted',
        prompt: 'Continue this thread',
      }),
    );
    expect(removeThreadMock).toHaveBeenCalledWith(legacyThread);
    expect(result.current.activeThreadKey).toBe(buildThreadKey('backend', 'conv-promoted'));
  });

  it('shows fallback assistant message when send fails', async () => {
    (chatClient.createConversation as jest.Mock).mockResolvedValue({
      conversationId: 'conv-err',
      title: 'Broken',
      createdAt: '2026-02-21T00:00:00.000Z',
    });
    (chatClient.sendMessage as jest.Mock).mockRejectedValue(
      new Error('Backend unavailable'),
    );

    const { result } = renderHook(() => useChatSession());
    act(() => {
      result.current.setInput('Broken');
    });

    await act(async () => {
      await result.current.sendMessage();
    });

    await waitFor(() => {
      expect(result.current.messages.length).toBeGreaterThanOrEqual(2);
    });

    expect(toUiError).toHaveBeenCalled();
    const last = result.current.messages[result.current.messages.length - 1];
    expect(last.role).toBe('assistant');
    expect(last.content).toContain('could not send');
  });
});
