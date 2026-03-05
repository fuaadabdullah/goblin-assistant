import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useChatSession } from '../useChatSession';
import { chatClient } from '../../api';
import { writeChatMessages } from '../../../../lib/chat-history';
import { toUiError } from '../../../../lib/ui-error';

jest.mock('../../api', () => ({
  chatClient: {
    createConversation: jest.fn(),
    sendMessage: jest.fn(),
  },
}));

jest.mock('../../../../lib/ui-error', () => ({
  toUiError: jest.fn(() => ({
    code: 'CHAT_SEND_FAILED',
    userMessage: 'Sorry, we could not send that message right now.',
  })),
}));

jest.mock('../../../../lib/chat-history', () => ({
  readChatMessages: jest.fn(() => []),
  writeChatMessages: jest.fn(),
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
jest.mock('../useChatThreads', () => ({
  useChatThreads: jest.fn(() => ({
    threads: [],
    isLoading: false,
    upsertThread: upsertThreadMock,
  })),
}));

jest.mock('../../../../contexts/ProviderContext', () => ({
  useProvider: jest.fn(() => ({
    selectedProvider: 'openai',
    selectedModel: 'gpt-4o-mini',
  })),
}));

describe('useChatSession', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    upsertThreadMock.mockClear();
  });

  it('initializes with expected default state', () => {
    const { result } = renderHook(() => useChatSession());

    expect(result.current.messages).toEqual([]);
    expect(result.current.input).toBe('');
    expect(result.current.isSending).toBe(false);
    expect(result.current.totalTokens).toBe(0);
    expect(result.current.totalCostUsd).toBe(0);
    expect(result.current.quickPrompts.length).toBeGreaterThan(0);
  });

  it('creates a thread, sends a message, persists history, and updates totals', async () => {
    (chatClient.createConversation as jest.Mock).mockResolvedValue({
      conversationId: 'conv-123',
      title: 'Test message',
      createdAt: '2026-02-21T00:00:00.000Z',
    });
    (chatClient.sendMessage as jest.Mock).mockResolvedValue({
      content: 'Assistant response',
      provider: 'openai',
      model: 'gpt-4o-mini',
      usage: { input_tokens: 10, output_tokens: 20, total_tokens: 30 },
      cost_usd: 0.0025,
    });

    const { result } = renderHook(() => useChatSession());

    act(() => {
      result.current.setInput('Test message');
    });
    expect(result.current.inputEstimate?.estimated_tokens).toBe(42);

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
        provider: 'openai',
        model: 'gpt-4o-mini',
      }),
    );
    expect(writeChatMessages).toHaveBeenCalled();
    expect(upsertThreadMock).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'conv-123',
      }),
    );
    expect(result.current.messages[0].role).toBe('user');
    expect(result.current.messages[1].role).toBe('assistant');
    expect(result.current.totalTokens).toBe(30);
    expect(result.current.totalCostUsd).toBe(0.0025);
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

