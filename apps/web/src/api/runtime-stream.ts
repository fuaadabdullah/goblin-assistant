import { env } from '@/config/env';
import { getAuthToken } from '@/utils/auth-session';
import { V1_CHAT_PREFIX } from '@/lib/api';
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

const createStreamBody = ({ conversationId, prompt, provider, model, goblin }: RuntimeStreamRequest) =>
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
      prompt.trim().length > 0
        ? `Mock response to: ${prompt.slice(0, 120)}`
        : 'Mock response.',
  },
  provider: 'mock',
  model: 'mock-gpt',
  done: true,
});

const readResponseText = async (response: Response): Promise<string> => {
  try {
    return await response.text();
  } catch {
    return '';
  }
};

const parseStreamPayload = (line: string): Record<string, unknown> | null => {
  if (!line.startsWith('data: ')) return null;

  try {
    return JSON.parse(line.slice(6)) as Record<string, unknown>;
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

const emitStreamChunk = (payload: Record<string, unknown>, onChunk: (chunk: StreamChunk) => void) => {
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

const processRuntimeStreamLine = (
  line: string,
  onChunk: (chunk: StreamChunk) => void
): TaskResponse | null => {
  if (!line) return null;

  const payload = parseStreamPayload(line);
  if (!payload) return null;

  const error = extractStreamError(payload);
  if (error) {
    throw new Error(error);
  }

  emitStreamChunk(payload, onChunk);

  if (payload['done'] === true) {
    return buildTaskResponse(payload);
  }

  return null;
};

const processRuntimeStreamBuffer = (
  buffer: string,
  onChunk: (chunk: StreamChunk) => void
): { buffer: string; finalResponse: TaskResponse | null } => {
  const lines = buffer.split('\n');
  let finalResponse: TaskResponse | null = null;

  for (let i = 0; i < lines.length - 1; i++) {
    const parsed = processRuntimeStreamLine(lines[i]?.trim() ?? '', onChunk);
    if (parsed) {
      finalResponse = parsed;
      break;
    }
  }

  return {
    buffer: lines[lines.length - 1] || '',
    finalResponse,
  };
};

const consumeRuntimeStream = async (
  reader: ReadableStreamDefaultReader<Uint8Array>,
  decoder: TextDecoder,
  callbacks: RuntimeStreamCallbacks
): Promise<TaskResponse | null> => {
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) return null;

    buffer += decoder.decode(value, { stream: true });
    const processed = processRuntimeStreamBuffer(buffer, callbacks.onChunk);
    buffer = processed.buffer;

    if (processed.finalResponse) {
      callbacks.onComplete?.(processed.finalResponse);
      await reader.cancel();
      return processed.finalResponse;
    }
  }
};

const readRuntimeStream = async (
  response: Response,
  { onChunk, onComplete }: RuntimeStreamCallbacks
): Promise<void> => {
  if (!response.body) {
    throw new Error('Streaming response body is empty');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const finalResponse = await consumeRuntimeStream(reader, decoder, { onChunk, onComplete });

  if (!finalResponse) {
    onComplete?.({ result: { message: 'Stream closed without completion event.' } });
  }
};

export const streamRuntimeTask = async (
  request: RuntimeStreamRequest,
  callbacks: RuntimeStreamCallbacks
): Promise<void> => {
  const token = getAuthToken();

  const response = await fetch(`${env.apiBaseUrl}${V1_CHAT_PREFIX}/stream`, {
    method: 'POST',
    headers: createStreamHeaders(token),
    body: createStreamBody(request),
    credentials: 'include',
  });

  if (!response.ok) {
    const errorText = await readResponseText(response);

    if (hasMockFallbackSignal(errorText)) {
      const mockResponse = buildMockStreamResponse(request.prompt);
      callbacks.onChunk({
        content:
          typeof mockResponse.result === 'object' && mockResponse.result !== null
            ? String((mockResponse.result as Record<string, unknown>)['message'] ?? 'Mock response.')
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

  await readRuntimeStream(response, callbacks);
};
