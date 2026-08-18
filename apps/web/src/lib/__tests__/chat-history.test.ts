import {
  buildThreadKey,
  clearPreloadedChat,
  preloadRecentChat,
  readPreloadedChat,
  readChatMessages,
  readChatMigrationMeta,
  readChatThreads,
  removeChatMessages,
  removeChatThread,
  markChatMigrationCompleted,
  resetChatMigrationMeta,
  sortChatThreads,
  writeChatMessages,
  writeChatThreads,
} from '../chat-history';

describe('chat-history', () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
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

  test('marks and reads migration metadata', () => {
    expect(readChatMigrationMeta()).toEqual({ migrationCompleted: false });

    const meta = markChatMigrationCompleted();
    expect(meta.migrationCompleted).toBe(true);

    const stored = readChatMigrationMeta();
    expect(stored.migrationCompleted).toBe(true);
    expect(typeof stored.completedAt).toBe('string');
  });

  test('resets migration metadata', () => {
    markChatMigrationCompleted();
    expect(readChatMigrationMeta().migrationCompleted).toBe(true);

    resetChatMigrationMeta();
    expect(readChatMigrationMeta()).toEqual({ migrationCompleted: false });
  });

  test('reads, sorts, writes, and removes legacy chat threads', () => {
    const threads = [
      {
        id: 'thread-old',
        source: 'legacy-local' as const,
        threadKey: buildThreadKey('legacy-local', 'thread-old'),
        title: 'Old thread',
        snippet: 'old',
        createdAt: '2026-01-01T00:00:00.000Z',
        updatedAt: '2026-01-01T00:00:00.000Z',
      },
      {
        id: 'thread-new',
        source: 'legacy-local' as const,
        threadKey: buildThreadKey('legacy-local', 'thread-new'),
        title: 'New thread',
        snippet: 'new',
        createdAt: '2026-01-02T00:00:00.000Z',
        updatedAt: '2026-01-02T00:00:00.000Z',
      },
      {
        id: 'backend-thread',
        source: 'backend' as const,
        threadKey: buildThreadKey('backend', 'backend-thread'),
        title: 'Ignored backend thread',
        snippet: '',
        createdAt: '2026-01-03T00:00:00.000Z',
        updatedAt: '2026-01-03T00:00:00.000Z',
      },
    ];

    expect(sortChatThreads([threads[0]!, threads[1]!]).map((thread) => thread.id)).toEqual([
      'thread-new',
      'thread-old',
    ]);

    writeChatThreads(threads as any);
    expect(readChatThreads().map((thread) => thread.id)).toEqual(['thread-new', 'thread-old']);

    removeChatThread('thread-new');
    expect(readChatThreads().map((thread) => thread.id)).toEqual(['thread-old']);
  });

  test('preloads and clears the most recent chat payload', () => {
    writeChatThreads([
      {
        id: 'thread-1',
        source: 'legacy-local',
        threadKey: buildThreadKey('legacy-local', 'thread-1'),
        title: 'Thread 1',
        snippet: 'Hello',
        createdAt: '2026-01-01T00:00:00.000Z',
        updatedAt: '2026-01-03T00:00:00.000Z',
      } as any,
    ]);

    writeChatMessages('thread-1', [
      {
        id: 'm1',
        createdAt: '2026-01-03T00:00:00.000Z',
        role: 'user',
        content: 'one',
      },
      {
        id: 'm2',
        createdAt: '2026-01-03T00:01:00.000Z',
        role: 'assistant',
        content: 'two',
      },
    ] as any);

    const preloaded = preloadRecentChat(1);
    expect(preloaded).toEqual({
      threadId: 'thread-1',
      messages: [
        {
          id: 'm2',
          createdAt: '2026-01-03T00:01:00.000Z',
          role: 'assistant',
          content: 'two',
        },
      ],
    });

    const stored = readPreloadedChat();
    expect(stored).toEqual(preloaded);

    clearPreloadedChat();
    expect(readPreloadedChat()).toBeNull();
  });

  test('ignores malformed preloaded chat payloads', () => {
    window.sessionStorage.setItem(
      'goblin_preload_chat_v1',
      JSON.stringify({
        threadId: 'thread-bad',
        messages: [{ role: 'user', content: 'ok' }, { nope: true }],
      })
    );

    expect(readPreloadedChat()).toEqual({
      threadId: 'thread-bad',
      messages: [
        {
          id: expect.any(String),
          createdAt: expect.any(String),
          role: 'user',
          content: 'ok',
        },
      ],
    });

    window.sessionStorage.setItem(
      'goblin_preload_chat_v1',
      JSON.stringify({ threadId: 123, messages: [] })
    );
    expect(readPreloadedChat()).toBeNull();
  });

  test('removes stored messages', () => {
    writeChatMessages('thread-2', [
      {
        id: 'm1',
        createdAt: '2026-01-03T00:00:00.000Z',
        role: 'user',
        content: 'hello',
      },
    ] as any);

    expect(readChatMessages('thread-2')).toHaveLength(1);
    removeChatMessages('thread-2');
    expect(readChatMessages('thread-2')).toHaveLength(0);
  });
});
