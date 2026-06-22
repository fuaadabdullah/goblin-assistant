import { act, renderHook, waitFor } from '@testing-library/react';
import type { ChatThread } from '../../../types';

const setQueryDataMock = vi.fn();
const mockTrackEvent = vi.fn();
const showError = vi.fn();
const showInfo = vi.fn();

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({
    setQueryData: setQueryDataMock,
  }),
}));

vi.mock('../../../api', () => ({
  chatClient: {
    chatCompletion: vi.fn(),
    createConversation: vi.fn(),
    importConversationMessages: vi.fn(),
    sendMessage: vi.fn(),
  },
}));

vi.mock('../../../../../utils/analytics', () => ({
  trackEvent: (...args: unknown[]) => mockTrackEvent(...args),
}));

vi.mock('../../../../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => ({ isAuthenticated: true }),
}));

vi.mock('../../../../../hooks/useToast', () => ({
  useToast: () => ({
    showError,
    showInfo,
  }),
}));

import { chatClient } from '../../../api';
import { formatSendMessageError, useSendMessage } from '../useSendMessage';

const activeThread: ChatThread | null = null;

describe('useSendMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it('tracks the first and second successful message sends', async () => {
    vi.mocked(chatClient.createConversation)
      .mockResolvedValueOnce({
        conversationId: 'conv-1',
        title: 'First question',
        createdAt: '2026-01-01T00:00:00.000Z',
      })
      .mockResolvedValueOnce({
        conversationId: 'conv-2',
        title: 'Second question',
        createdAt: '2026-01-01T00:00:01.000Z',
      });
    vi.mocked(chatClient.sendMessage)
      .mockResolvedValueOnce({
        messageId: 'assistant-1',
        content: 'First answer',
        provider: 'openai',
        model: 'gpt-4o-mini',
        createdAt: '2026-01-01T00:00:00.500Z',
        usage: { total_tokens: 10 },
        cost_usd: 0.001,
      })
      .mockResolvedValueOnce({
        messageId: 'assistant-2',
        content: 'Second answer',
        provider: 'openai',
        model: 'gpt-4o-mini',
        createdAt: '2026-01-01T00:00:01.500Z',
        usage: { total_tokens: 20 },
        cost_usd: 0.002,
      });

    const applyMessages = vi.fn();
    const setIsSending = vi.fn();

    const { result } = renderHook(() =>
      useSendMessage({
        input: '',
        isSending: false,
        isMessagesLoading: false,
        messages: [],
        activeThread,
        selectedModel: 'gpt-4o-mini',
        selectedProvider: 'openai',
        pendingAttachments: [],
        applyMessages,
        setIsSending,
        showError,
        showInfo,
      })
    );

    await act(async () => {
      await result.current('First question');
    });
    await act(async () => {
      await result.current('Second question');
    });

    await waitFor(() => {
      expect(mockTrackEvent).toHaveBeenCalledWith('first_message_sent');
      expect(mockTrackEvent).toHaveBeenCalledWith('second_message_sent');
    });
  });

  it('does not track analytics when sending fails', async () => {
    vi.mocked(chatClient.createConversation).mockResolvedValue({
      conversationId: 'conv-1',
      title: 'Broken',
      createdAt: '2026-01-01T00:00:00.000Z',
    });
    vi.mocked(chatClient.sendMessage).mockRejectedValue(new Error('Backend unavailable'));

    const applyMessages = vi.fn();
    const setIsSending = vi.fn();

    const { result } = renderHook(() =>
      useSendMessage({
        input: '',
        isSending: false,
        isMessagesLoading: false,
        messages: [],
        activeThread,
        selectedModel: 'gpt-4o-mini',
        selectedProvider: 'openai',
        pendingAttachments: [],
        applyMessages,
        setIsSending,
        showError,
        showInfo,
      })
    );

    await act(async () => {
      await result.current('Broken');
    });

    expect(mockTrackEvent).not.toHaveBeenCalled();
    expect(showError).toHaveBeenCalled();
  });

  it('preserves non-Error send failures in the formatter', () => {
    expect(formatSendMessageError('chat backend unavailable')).toBe('chat backend unavailable');
  });
});
