import { beforeEach, describe, expect, it, vi } from 'vitest';
import { streamRuntimeTask } from '../runtime-stream';

describe('streamRuntimeTask', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    (globalThis as typeof globalThis & { fetch: typeof fetch }).fetch = vi.fn();
  });

  it('falls back to a mock response when the backend reports no providers', async () => {
    const onChunk = vi.fn();
    const onComplete = vi.fn();

    (globalThis.fetch as unknown as vi.Mock).mockResolvedValue({
      ok: false,
      status: 200,
      text: vi.fn().mockResolvedValue('no-configured-providers'),
    });

    await streamRuntimeTask(
      {
        conversationId: 'conv-1',
        prompt: 'hi',
        goblin: 'docs',
      },
      { onChunk, onComplete }
    );

    expect(onChunk).toHaveBeenCalledWith(
      expect.objectContaining({
        done: true,
        content: 'Mock response to: hi',
      })
    );
    expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: 'mock',
        model: 'mock-gpt',
        done: true,
      })
    );
  });
});
