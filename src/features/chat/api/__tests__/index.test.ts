import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { chatClient } from '../index';
import { apiClient } from '../../../../lib/api';

describe('chatClient conversation API', () => {
  beforeEach(() => {
    jest.restoreAllMocks();
  });

  it('passes prompt through to the persistent send endpoint', async () => {
    const spy = jest.spyOn(apiClient, 'sendConversationMessage').mockResolvedValue({
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
    const spy = jest.spyOn(apiClient, 'sendConversationMessage').mockResolvedValue({
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
    const spy = jest
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
});
