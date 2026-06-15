import { env } from '@/config/env';
import { V1_CHAT_PREFIX } from '@/lib/api';
import type { StreamChunk, TaskResponse } from '@/types/api';

interface RuntimeStreamRequest {
  conversationId: string;
  prompt: string;
  provider?: string | undefined;
  model?: string | undefined;
  token?: string | null | undefined;
  goblin: string;
  onChunk: (chunk: StreamChunk) => void;
  onComplete?: ((response: TaskResponse) => void) | undefined;
}

const buildHeaders = (token?: string | null): Record<string, string> => {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
};

const readStreamErrorMessage = (payload: Record<string, unknown>): string | undefined => {
  if (payload['type'] !== 'error' && typeof payload['error'] !== 'string') {
    return undefined;
  }
  return (
    (typeof payload['message'] === 'string' && payload['message']) ||
    (typeof payload['error'] === 'string' && payload['error']) ||
    'Streaming failed'
  );
};

const readChunkContent = (payload: Record<string, unknown>): string | undefined =>
  typeof payload['content'] === 'string'
    ? payload['content']
    : typeof payload['result'] === 'string'
      ? payload['result']
      : undefined;

const buildCompletedResponse = (payload: Record<string, unknown>): TaskResponse => ({
  result: payload['result'],
  message_id: payload['message_id'],
  provider: payload['provider'],
  model: payload['model'],
  tokens: payload['tokens'],
  cost: payload['cost'],
  duration_ms: payload['duration_ms'],
  done: true,
});

const parseStreamEvent = (payloadText: string, onChunk: (chunk: StreamChunk) => void): TaskResponse | null => {
  const payload = JSON.parse(payloadText) as Record<string, unknown>;
  const errorMessage = readStreamErrorMessage(payload);
  if (errorMessage) throw new Error(errorMessage);

  onChunk({
    content: readChunkContent(payload),
    done: payload['done'] === true,
    token_count: Number(payload['token_count']) || undefined,
    cost_delta: Number(payload['cost_delta']) || undefined,
    result: payload['result'],
  });

  return payload['done'] === true ? buildCompletedResponse(payload) : null;
};

const consumeStream = async (
  reader: ReadableStreamDefaultReader<Uint8Array>,
  onChunk: (chunk: StreamChunk) => void
): Promise<TaskResponse | null> => {
  const decoder = new TextDecoder();
  let buffer = '';
  let finalResponse: TaskResponse | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || !trimmed.startsWith('data: ')) continue;
      const completed = parseStreamEvent(trimmed.slice(6), onChunk);
      if (completed) {
        finalResponse = completed;
        await reader.cancel();
        return finalResponse;
      }
    }
  }

  const remaining = buffer.trim();
  if (!remaining.startsWith('data: ')) return finalResponse;

  const completed = parseStreamEvent(remaining.slice(6), onChunk);
  return completed ?? finalResponse;
};

export const streamRuntimeTask = async ({
  conversationId,
  prompt,
  provider,
  model,
  token,
  goblin,
  onChunk,
  onComplete,
}: RuntimeStreamRequest): Promise<void> => {
  const response = await fetch(`${env.apiBaseUrl}${V1_CHAT_PREFIX}/stream`, {
    method: 'POST',
    headers: buildHeaders(token),
    body: JSON.stringify({
      conversation_id: conversationId,
      message: prompt,
      provider,
      model,
      metadata: { source: 'runtime-client', goblin },
    }),
    credentials: 'include',
  });

  if (!response.ok) {
    throw new Error(`Streaming request failed with HTTP ${response.status}`);
  }
  if (!response.body) {
    throw new Error('Streaming response body is empty');
  }

  const finalResponse = await consumeStream(response.body.getReader(), onChunk);
  if (finalResponse && onComplete) {
    onComplete(finalResponse);
  }
};
