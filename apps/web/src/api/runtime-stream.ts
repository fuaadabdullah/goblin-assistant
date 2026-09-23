import { createParser } from 'eventsource-parser';
import { getAuthTokenForRequest } from '@/utils/auth-session';
import { hasMockFallbackSignal } from '@/lib/api/fallback';
import type { StreamChunk, TaskResponse } from '@/types/api';

type RuntimeStreamCallbacks = {
  onChunk: (chunk: StreamChunk) => void;
  onComplete?: ((response: TaskResponse) => void) | undefined;
};

type RuntimeStreamRequest = {
  conversationId: string;
  prompt: string;
  provider?: string | undefined;
  model?: string | undefined;
  goblin: string;
};

const createStreamHeaders = (token: string | null): Record<string, string> => {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return headers;
};

const createStreamBody = ({
  conversationId,
  prompt,
  provider,
  model,
  goblin,
}: RuntimeStreamRequest) =>
  JSON.stringify({
    conversation_id: conversationId,
    message: prompt,
    provider,
    model,
    metadata: { source: 'runtime-client', goblin },
  });

const buildMockStreamResponse = (prompt: string): TaskResponse => ({
  result: {
    message:
      prompt.trim().length > 0 ? `Mock response to: ${prompt.slice(0, 120)}` : 'Mock response.',
  },
  provider: 'mock',
  model: 'mock-gpt',
  done: true,
});

const INTERNAL_CHAT_STREAM_PATH = '/api/chat/stream';

const readResponseText = async (response: Response): Promise<string> => {
  try {
    return await response.text();
  } catch {
    return '';
  }
};

const parseEventPayload = (data: string): Record<string, unknown> | null => {
  try {
    return JSON.parse(data) as Record<string, unknown>;
  } catch {
    return null;
  }
};

const extractStreamError = (payload: Record<string, unknown>): string | null => {
  if (payload['type'] === 'error' || typeof payload['error'] === 'string') {
    return (
      (typeof payload['message'] === 'string' && payload['message']) ||
      (typeof payload['error'] === 'string' && payload['error']) ||
      'Streaming failed'
    );
  }

  return null;
};

const buildTaskResponse = (payload: Record<string, unknown>): TaskResponse => ({
  result: payload['result'],
  message_id: payload['message_id'],
  provider: payload['provider'],
  model: payload['model'],
  tokens: payload['tokens'],
  cost: payload['cost'],
  duration_ms: payload['duration_ms'],
  done: true,
});

const emitStreamChunk = (
  payload: Record<string, unknown>,
  onChunk: (chunk: StreamChunk) => void
) => {
  const chunkContent =
    typeof payload['content'] === 'string'
      ? payload['content']
      : typeof payload['result'] === 'string'
        ? payload['result']
        : undefined;

  onChunk({
    content: chunkContent,
    done: payload['done'] === true,
    token_count: Number(payload['token_count']) || undefined,
    cost_delta: Number(payload['cost_delta']) || undefined,
    result: payload['result'],
  });
};

const consumeRuntimeStream = async (
  reader: ReadableStreamDefaultReader<Uint8Array>,
  decoder: TextDecoder,
  callbacks: RuntimeStreamCallbacks,
  signal: AbortSignal | undefined
): Promise<TaskResponse> => {
  let finalResponse: TaskResponse | null = null;

  const parser = createParser({
    onEvent(event) {
      if (finalResponse || !event.data) return;

      const payload = parseEventPayload(event.data);
      if (!payload) return;

      const error = extractStreamError(payload);
      if (error) {
        throw new Error(error);
      }

      emitStreamChunk(payload, callbacks.onChunk);

      if (payload['done'] === true) {
        finalResponse = buildTaskResponse(payload);
      }
    },
  });

  while (!finalResponse) {
    if (signal?.aborted) {
      await reader.cancel();
      throw new DOMException('Runtime stream aborted', 'AbortError');
    }

    const { done, value } = await reader.read();
    if (done) {
      // The connection dropped (or the server closed it) before sending a
      // "done" event. Surface this as a real failure rather than faking a
      // completion — callers already have error handling/fallback paths that
      // depend on this actually rejecting.
      throw new Error('Runtime stream ended before the server sent a completion event.');
    }

    parser.feed(decoder.decode(value, { stream: true }));
  }

  await reader.cancel();
  return finalResponse;
};

const readRuntimeStream = async (
  response: Response,
  { onChunk, onComplete }: RuntimeStreamCallbacks,
  signal: AbortSignal | undefined
): Promise<void> => {
  if (!response.body) {
    throw new Error('Streaming response body is empty');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const finalResponse = await consumeRuntimeStream(reader, decoder, { onChunk, onComplete }, signal);
  onComplete?.(finalResponse);
};

export const streamRuntimeTask = async (
  request: RuntimeStreamRequest,
  callbacks: RuntimeStreamCallbacks,
  signal?: AbortSignal
): Promise<void> => {
  const token = await getAuthTokenForRequest();

  const response = await fetch(INTERNAL_CHAT_STREAM_PATH, {
    method: 'POST',
    headers: createStreamHeaders(token),
    body: createStreamBody(request),
    credentials: 'include',
    signal: signal ?? null,
  });

  if (!response.ok) {
    const errorText = await readResponseText(response);

    if (hasMockFallbackSignal(errorText)) {
      const mockResponse = buildMockStreamResponse(request.prompt);
      callbacks.onChunk({
        content:
          typeof mockResponse.result === 'object' && mockResponse.result !== null
            ? String(
                (mockResponse.result as Record<string, unknown>)['message'] ?? 'Mock response.'
              )
            : 'Mock response.',
        done: true,
        result: mockResponse.result,
      });
      callbacks.onComplete?.(mockResponse);
      return;
    }

    throw new Error(
      `Streaming request failed with HTTP ${response.status}${errorText ? `: ${errorText}` : ''}`
    );
  }

  await readRuntimeStream(response, callbacks, signal);
};
