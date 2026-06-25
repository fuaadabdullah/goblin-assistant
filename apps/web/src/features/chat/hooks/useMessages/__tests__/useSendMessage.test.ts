import { act, renderHook, waitFor } from '@testing-library/react';
import type { ChatThread } from '../../../types';

const setQueryDataMock = vi.fn();
const mockTrackEvent = vi.fn();
const showError = vi.fn();
const showInfo = vi.fn();
const mockAuthState = vi.hoisted(() => ({ isAuthenticated: true }));

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
  useAuthSession: () => ({ isAuthenticated: mockAuthState.isAuthenticated }),
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
    mockAuthState.isAuthenticated = true;
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

    const onSendSuccess = vi.fn();
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

  it('surfaces unavailable real runtime for guest sends instead of accepting mock fallback', async () => {
    mockAuthState.isAuthenticated = false;
    vi.mocked(chatClient.chatCompletion).mockRejectedValue(
      new Error('Real model runtime is unavailable. Please try again later.')
    );

    const applyMessages = vi.fn();
    const setIsSending = vi.fn();
    const onSendSuccess = vi.fn();

    const { result } = renderHook(() =>
      useSendMessage({
        input: 'Hello',
        isSending: false,
        isMessagesLoading: false,
        messages: [],
        activeThread,
        pendingAttachments: [],
        applyMessages,
        onSendSuccess,
        setIsSending,
        showError,
        showInfo,
      })
    );

    await act(async () => {
      await result.current();
    });

    expect(onSendSuccess).not.toHaveBeenCalled();
    expect(showError).toHaveBeenCalledWith(
      'Message failed',
      'Real model runtime is unavailable. Please try again later.'
    );
    expect(mockTrackEvent).not.toHaveBeenCalled();
  });

  it('clears input after a successful send', async () => {
    vi.mocked(chatClient.createConversation).mockResolvedValue({
      conversationId: 'conv-1',
      title: 'Success',
      createdAt: '2026-01-01T00:00:00.000Z',
    });
    vi.mocked(chatClient.sendMessage).mockResolvedValue({
      messageId: 'assistant-1',
      content: 'Real answer',
      provider: 'openai',
      model: 'gpt-4o-mini',
      createdAt: '2026-01-01T00:00:00.500Z',
    });

    const onSendSuccess = vi.fn();
    const { result } = renderHook(() =>
      useSendMessage({
        input: 'Success',
        isSending: false,
        isMessagesLoading: false,
        messages: [],
        activeThread,
        pendingAttachments: [],
        applyMessages: vi.fn(),
        onSendSuccess,
        setIsSending: vi.fn(),
        showError,
        showInfo,
      })
    );

    await act(async () => {
      await result.current();
    });

    expect(onSendSuccess).toHaveBeenCalledOnce();
  });

  it('preserves non-Error send failures in the formatter', () => {
    expect(formatSendMessageError('chat backend unavailable')).toBe('chat backend unavailable');
  });
});
