import type { ChatMessage, ChatThread, ChatMessageMeta } from '../chat';

describe('ChatMessage type', () => {
  it('creates a valid user message', () => {
    const msg: ChatMessage = {
      id: 'msg1',
      createdAt: '2024-01-01T00:00:00Z',
      role: 'user',
      content: 'Hello',
    };
    expect(msg.role).toBe('user');
    expect(msg.content).toBe('Hello');
  });

  it('creates a valid assistant message with meta', () => {
    const meta: ChatMessageMeta = {
      provider: 'openai',
      model: 'gpt-4',
      usage: { input_tokens: 10, output_tokens: 20 },
      cost_usd: 0.0005,
      cost_is_approx: true,
    };
    const msg: ChatMessage = {
      id: 'msg2',
      createdAt: '2024-01-01T00:00:01Z',
      role: 'assistant',
      content: 'Hi there!',
      meta,
      isStreaming: false,
    };
    expect(msg.meta?.provider).toBe('openai');
    expect(msg.meta?.cost_usd).toBe(0.0005);
    expect(msg.isStreaming).toBe(false);
  });

  it('creates a streaming message', () => {
    const msg: ChatMessage = {
      id: 'msg3',
      createdAt: '2024-01-01T00:00:02Z',
      role: 'assistant',
      content: '',
      isStreaming: true,
    };
    expect(msg.isStreaming).toBe(true);
  });

  it('supports system role messages', () => {
    const msg: ChatMessage = {
      id: 'msg4',
      createdAt: '2024-01-01T00:00:03Z',
      role: 'system',
      content: 'You are a helpful assistant.',
    };
    expect(msg.role).toBe('system');
  });

  it('supports attachments in meta', () => {
    const meta: ChatMessageMeta = {
      attachments: [
        { id: 'att1', filename: 'doc.pdf', mime_type: 'application/pdf', size_bytes: 1024 },
      ],
    };
    expect(meta.attachments![0].filename).toBe('doc.pdf');
    expect(meta.attachments![0].size_bytes).toBe(1024);
  });

  it('supports visualizations in meta', () => {
    const meta: ChatMessageMeta = {
      visualizations: [
        { type: 'bar', title: 'Revenue', data: [{ month: 'Jan', value: 100 }], config: {} },
      ],
    };
    expect(meta.visualizations![0].type).toBe('bar');
    expect(meta.visualizations![0].data[0].value).toBe(100);
  });

  it('supports correlation_id in meta', () => {
    const meta: ChatMessageMeta = {
      correlation_id: 'corr-123',
    };
    expect(meta.correlation_id).toBe('corr-123');
  });

  it('supports estimated cost fields in meta', () => {
    const meta: ChatMessageMeta = {
      estimated_cost_usd: 0.01,
      estimated_tokens: 500,
    };
    expect(meta.estimated_cost_usd).toBe(0.01);
    expect(meta.estimated_tokens).toBe(500);
  });
});

describe('ChatThread type', () => {
  it('creates a valid backend thread', () => {
    const thread: ChatThread = {
      id: 'thread1',
      threadKey: 'key1',
      source: 'backend',
      title: 'Test Thread',
      snippet: 'Hello...',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T01:00:00Z',
    };
    expect(thread.source).toBe('backend');
    expect(thread.title).toBe('Test Thread');
  });

  it('creates a valid legacy-local thread', () => {
    const thread: ChatThread = {
      id: 'thread2',
      threadKey: 'key2',
      source: 'legacy-local',
      title: 'Old Thread',
      snippet: 'Hi...',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T01:00:00Z',
    };
    expect(thread.source).toBe('legacy-local');
  });
});
