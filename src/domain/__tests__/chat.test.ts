import type { ChatRole, ChatMessage, ChatThread, ChatThreadSource, ChatUsage, ChatMessageMeta } from '../chat';

describe('domain/chat types', () => {
  it('should allow valid ChatRole values', () => {
    const roles: ChatRole[] = ['user', 'assistant', 'system'];
    expect(roles).toHaveLength(3);
  });

  it('should build a valid ChatMessage', () => {
    const msg: ChatMessage = {
      id: '1',
      createdAt: new Date().toISOString(),
      role: 'user',
      content: 'Hello',
    };
    expect(msg.id).toBe('1');
    expect(msg.role).toBe('user');
    expect(msg.content).toBe('Hello');
    expect(msg.isStreaming).toBeUndefined();
  });

  it('should build a ChatMessage with metadata', () => {
    const meta: ChatMessageMeta = {
      provider: 'openai',
      model: 'gpt-4',
      usage: { input_tokens: 10, output_tokens: 20, total_tokens: 30 },
      cost_usd: 0.01,
      estimated_cost_usd: 0.009,
      estimated_tokens: 28,
      correlation_id: 'abc-123',
      cost_is_approx: true,
      attachments: [{ id: 'f1', filename: 'doc.pdf', mime_type: 'application/pdf', size_bytes: 1024 }],
    };
    const msg: ChatMessage = {
      id: '2',
      createdAt: new Date().toISOString(),
      role: 'assistant',
      content: 'Hi',
      meta,
      isStreaming: true,
    };
    expect(msg.meta?.provider).toBe('openai');
    expect(msg.meta?.attachments).toHaveLength(1);
    expect(msg.isStreaming).toBe(true);
  });

  it('should build a valid ChatUsage', () => {
    const usage: ChatUsage = { input_tokens: 5, output_tokens: 10, total_tokens: 15 };
    expect(usage.total_tokens).toBe(15);
  });

  it('should build a valid ChatThread', () => {
    const thread: ChatThread = {
      id: 't1',
      threadKey: 'key-1',
      source: 'backend',
      title: 'Test Thread',
      snippet: 'Hello...',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    expect(thread.source).toBe('backend');
  });

  it('should accept both ChatThreadSource values', () => {
    const sources: ChatThreadSource[] = ['backend', 'legacy-local'];
    expect(sources).toHaveLength(2);
  });
});
