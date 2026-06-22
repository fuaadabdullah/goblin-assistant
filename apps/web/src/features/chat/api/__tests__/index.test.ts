import { describe, it, expect, beforeEach, vi } from 'vitest';
import { chatClient } from '../index';
import { apiClient } from '@/lib/api';

describe('chatClient conversation API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('passes prompt through to the persistent send endpoint', async () => {
    const spy = vi.spyOn(apiClient, 'sendConversationMessage').mockResolvedValue({
      content: 'ok',
      provider: 'openai',
      model: 'gpt-4o-mini',
    });

    await chatClient.sendMessage({
      conversationId: 'conv-1',
      prompt: 'Hi',
    });

    expect(spy).toHaveBeenCalledWith({
      conversationId: 'conv-1',
      message: 'Hi',
      model: undefined,
      provider: undefined,
    });
  });

  it('falls back to the last user message when prompt is omitted', async () => {
    const spy = vi.spyOn(apiClient, 'sendConversationMessage').mockResolvedValue({
      content: 'ok',
      provider: 'openai',
      model: 'gpt-4o-mini',
    });

    await chatClient.sendMessage({
      conversationId: 'conv-2',
      messages: [
        { id: 'm1', createdAt: '2026-02-21T00:00:00.000Z', role: 'assistant', content: 'Hello' },
        { id: 'm2', createdAt: '2026-02-21T00:00:01.000Z', role: 'user', content: 'Need help' },
      ],
    });

    expect(spy).toHaveBeenCalledWith({
      conversationId: 'conv-2',
      message: 'Need help',
      model: undefined,
      provider: undefined,
    });
  });

  it('retries once without explicit model/provider when explicit selection fails', async () => {
    const spy = vi
      .spyOn(apiClient, 'sendConversationMessage')
      .mockRejectedValueOnce(new Error('invalid provider selection'))
      .mockResolvedValueOnce({
        content: 'retry-ok',
        provider: 'aliyun',
        model: 'qwen-plus',
      });

    await chatClient.sendMessage({
      conversationId: 'conv-3',
      prompt: 'Retry me',
      model: 'gpt-4o-mini',
      provider: 'openai',
    });

    expect(spy).toHaveBeenCalledTimes(2);
    expect(spy).toHaveBeenNthCalledWith(1, {
      conversationId: 'conv-3',
      message: 'Retry me',
      model: 'gpt-4o-mini',
      provider: 'openai',
    });
    expect(spy).toHaveBeenNthCalledWith(2, {
      conversationId: 'conv-3',
      message: 'Retry me',
    });
  });

  it('surfaces conversation send failures instead of falling back to mock completion', async () => {
    const sendSpy = vi
      .spyOn(apiClient, 'sendConversationMessage')
      .mockRejectedValueOnce(new Error('no-configured-providers'));
    const completionSpy = vi.spyOn(apiClient, 'chatCompletion');

    await expect(
      chatClient.sendMessage({
        conversationId: 'conv-4',
        prompt: 'Hi',
        messages: [
          { id: 'm1', createdAt: '2026-02-21T00:00:00.000Z', role: 'user', content: 'Hi' },
        ],
      })
    ).rejects.toMatchObject({
      code: 'CHAT_SEND_FAILED',
      userMessage: 'We could not send that message. Please try again.',
    });

    expect(sendSpy).toHaveBeenCalledTimes(1);
    expect(completionSpy).not.toHaveBeenCalled();
  });

  it('surfaces provider access errors when fallback completion also fails', async () => {
    vi.spyOn(apiClient, 'sendConversationMessage').mockRejectedValueOnce({
      response: {
        status: 200,
        data: { error: 'provider-access-denied' },
      },
    });
    vi.spyOn(apiClient, 'chatCompletion').mockRejectedValueOnce(new Error('fallback failed'));

    await expect(
      chatClient.sendMessage({
        conversationId: 'conv-5',
        prompt: 'Hi',
      })
    ).rejects.toMatchObject({
      code: 'CHAT_PROVIDER_ACCESS_DENIED',
        userMessage: 'Your account does not have access to any providers right now.',
      });
  });

  it('surfaces streaming provider errors instead of falling back to mock completion', async () => {
    const onChunk = vi.fn();
    const onComplete = vi.fn();
    const onError = vi.fn();
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 200,
      statusText: 'OK',
      text: vi.fn().mockResolvedValue('no-configured-providers'),
    });

    vi.spyOn(apiClient, 'chatCompletion');
    vi.stubGlobal('fetch', fetchMock as unknown as typeof fetch);

    await expect(
      chatClient.sendMessageStreaming({
        conversationId: 'conv-6',
        prompt: 'Stream this',
        onChunk,
        onComplete,
        onError,
      })
    ).rejects.toMatchObject({
      code: 'CHAT_STREAM_FAILED',
      userMessage: 'The connection was interrupted. Please try again.',
    });

    expect(fetchMock).toHaveBeenCalled();
    expect(apiClient.chatCompletion).not.toHaveBeenCalled();
    expect(onChunk).not.toHaveBeenCalled();
    expect(onComplete).not.toHaveBeenCalled();
  });

  it('preserves non-Error streaming failures in the error callback', async () => {
    const onChunk = vi.fn();
    const onComplete = vi.fn();
    const onError = vi.fn();
    const fetchMock = vi.fn().mockRejectedValue('stream backend unavailable');

    vi.stubGlobal('fetch', fetchMock as unknown as typeof fetch);

    await expect(
      chatClient.sendMessageStreaming({
        conversationId: 'conv-7',
        prompt: 'Stream this',
        onChunk,
        onComplete,
        onError,
      })
    ).rejects.toMatchObject({
      code: 'CHAT_STREAM_FAILED',
      userMessage: 'The connection was interrupted. Please try again.',
    });

    expect(onError).toHaveBeenCalledWith(expect.any(Error));
    expect((onError.mock.calls[0]?.[0] as Error).message).toBe('stream backend unavailable');
    expect(onComplete).not.toHaveBeenCalled();
  });
});
