import { readChatMessages, writeChatMessages } from '../chat-history';

describe('chat-history', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  test('round-trips messages with meta', () => {
    const conversationId = 'conv-1';
    const messages = [
      {
        id: 'm1',
        createdAt: new Date('2026-01-01T00:00:00.000Z').toISOString(),
        role: 'user' as const,
        content: 'Hello',
        meta: { estimated_tokens: 12, estimated_cost_usd: 0.00024 },
      },
      {
        id: 'm2',
        createdAt: new Date('2026-01-01T00:00:01.000Z').toISOString(),
        role: 'assistant' as const,
        content: 'Hi!',
        meta: {
          provider: 'openai',
          model: 'gpt-4o-mini',
          usage: { input_tokens: 10, output_tokens: 5, total_tokens: 15 },
          cost_usd: 0.000123,
          correlation_id: 'cid-123',
        },
      },
    ];

    writeChatMessages(conversationId, messages as any);
    const read = readChatMessages(conversationId);

    expect(read).toHaveLength(2);
    expect(read[0].id).toBe('m1');
    expect(read[0].meta?.estimated_tokens).toBe(12);
    expect(read[1].meta?.provider).toBe('openai');
    expect(read[1].meta?.usage?.total_tokens).toBe(15);
    expect(read[1].meta?.correlation_id).toBe('cid-123');
  });

  test('normalizes legacy messages missing id/createdAt', () => {
    const conversationId = 'conv-legacy';
    window.localStorage.setItem(
      `goblin_chat_messages_v1:${conversationId}`,
      JSON.stringify([{ role: 'user', content: 'Legacy' }])
    );

    const read = readChatMessages(conversationId);
    expect(read).toHaveLength(1);
    expect(typeof read[0].id).toBe('string');
    expect(typeof read[0].createdAt).toBe('string');
  });
});

