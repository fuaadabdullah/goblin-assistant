import { beforeEach, describe, expect, it, vi } from 'vitest';
import { streamRuntimeTask } from '../runtime-stream';

/** Builds a mock streaming Response whose body yields the given SSE lines. */
const mockSseResponse = (lines: string[]): Response => {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const line of lines) {
        controller.enqueue(encoder.encode(line));
      }
      controller.close();
    },
  });

  return { ok: true, status: 200, body } as unknown as Response;
};

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

  it('parses SSE chunks and resolves once a done event arrives', async () => {
    const onChunk = vi.fn();
    const onComplete = vi.fn();

    (globalThis.fetch as unknown as vi.Mock).mockResolvedValue(
      mockSseResponse([
        'data: {"content":"Hello"}\n\n',
        'data: {"content":" world"}\n\n',
        'data: {"done":true,"result":"Hello world","provider":"openai"}\n\n',
      ])
    );

    await streamRuntimeTask(
      { conversationId: 'conv-2', prompt: 'hi', goblin: 'docs' },
      { onChunk, onComplete }
    );

    expect(onChunk).toHaveBeenNthCalledWith(1, expect.objectContaining({ content: 'Hello' }));
    expect(onChunk).toHaveBeenNthCalledWith(2, expect.objectContaining({ content: ' world' }));
    expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({ result: 'Hello world', provider: 'openai', done: true })
    );
  });

  it('rejects instead of faking a completion when the connection drops early', async () => {
    const onChunk = vi.fn();
    const onComplete = vi.fn();

    (globalThis.fetch as unknown as vi.Mock).mockResolvedValue(
      mockSseResponse(['data: {"content":"partial"}\n\n'])
    );

    await expect(
      streamRuntimeTask(
        { conversationId: 'conv-3', prompt: 'hi', goblin: 'docs' },
        { onChunk, onComplete }
      )
    ).rejects.toThrow('Runtime stream ended before the server sent a completion event.');

    expect(onComplete).not.toHaveBeenCalled();
  });

  it('rejects when the server sends an error event', async () => {
    const onChunk = vi.fn();
    const onComplete = vi.fn();

    (globalThis.fetch as unknown as vi.Mock).mockResolvedValue(
      mockSseResponse(['data: {"type":"error","message":"provider unavailable"}\n\n'])
    );

    await expect(
      streamRuntimeTask(
        { conversationId: 'conv-4', prompt: 'hi', goblin: 'docs' },
        { onChunk, onComplete }
      )
    ).rejects.toThrow('provider unavailable');

    expect(onComplete).not.toHaveBeenCalled();
  });

  it('rejects with an AbortError once the signal is aborted', async () => {
    const onChunk = vi.fn();
    const onComplete = vi.fn();
    const controller = new AbortController();

    (globalThis.fetch as unknown as vi.Mock).mockResolvedValue(
      mockSseResponse(['data: {"content":"partial"}\n\n'])
    );

    controller.abort();

    await expect(
      streamRuntimeTask(
        { conversationId: 'conv-5', prompt: 'hi', goblin: 'docs' },
        { onChunk, onComplete },
        controller.signal
      )
    ).rejects.toThrow('Runtime stream aborted');

    expect(onComplete).not.toHaveBeenCalled();
  });
});
