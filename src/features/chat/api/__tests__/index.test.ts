import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { chatClient } from '../index';

jest.mock('../../../../api/apiClient', () => ({
  apiClient: {
    createConversation: jest.fn(),
    generate: jest.fn(),
  },
}));

describe('chatClient local generate proxy payload', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        content: 'ok',
        provider: 'openai',
        model: 'gpt-4o-mini',
      }),
    }) as unknown as typeof fetch;
  });

  it('does not force a default model when none is selected', async () => {
    await chatClient.sendMessage({
      conversationId: 'conv-1',
      prompt: 'Hi',
    });

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [, options] = (global.fetch as jest.Mock).mock.calls[0];
    const payload = JSON.parse(String(options.body));

    expect(payload.prompt).toBe('Hi');
    expect(payload).not.toHaveProperty('model');
    expect(payload).not.toHaveProperty('provider');
  });

  it('forwards explicit model/provider selections', async () => {
    await chatClient.sendMessage({
      conversationId: 'conv-2',
      prompt: 'Hi',
      model: 'gpt-4o-mini',
      provider: 'openai',
    });

    const [, options] = (global.fetch as jest.Mock).mock.calls[0];
    const payload = JSON.parse(String(options.body));

    expect(payload.model).toBe('gpt-4o-mini');
    expect(payload.provider).toBe('openai');
  });

  it('retries once without explicit model/provider when explicit selection fails', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: false,
        status: 422,
        json: async () => ({ detail: { message: 'invalid provider selection' } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          content: 'retry-ok',
          provider: 'aliyun',
          model: 'qwen-plus',
        }),
      });

    await chatClient.sendMessage({
      conversationId: 'conv-3',
      prompt: 'Retry me',
      model: 'gpt-4o-mini',
      provider: 'openai',
    });

    expect(global.fetch).toHaveBeenCalledTimes(2);

    const [, firstOptions] = (global.fetch as jest.Mock).mock.calls[0];
    const [, secondOptions] = (global.fetch as jest.Mock).mock.calls[1];
    const firstPayload = JSON.parse(String(firstOptions.body));
    const secondPayload = JSON.parse(String(secondOptions.body));

    expect(firstPayload.model).toBe('gpt-4o-mini');
    expect(firstPayload.provider).toBe('openai');
    expect(secondPayload.prompt).toBe('Retry me');
    expect(secondPayload).not.toHaveProperty('model');
    expect(secondPayload).not.toHaveProperty('provider');
  });
});
