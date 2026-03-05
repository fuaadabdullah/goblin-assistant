import { apiClient } from '../../../api/apiClient';
import { UiError } from '../../../lib/ui-error';
import type { ChatMessage } from '../types';

export interface ChatResponse {
  content?: string;
  model?: string;
  provider?: string;
  usage?: { input_tokens?: number; output_tokens?: number; total_tokens?: number };
  cost_usd?: number;
  correlation_id?: string;
}

export interface CreateConversationParams {
  title?: string;
}

export interface CreateConversationResult {
  conversationId: string;
  title?: string;
  createdAt: string;
}

export interface SendMessageParams {
  conversationId: string;
  prompt?: string;
  messages?: ChatMessage[];
  model?: string;
  provider?: string;
}

/**
 * Call the same-origin Next.js /api/generate route.
 * It prefers the Fly backend unified route and uses GCP providers as fallback.
 */
async function callLocalGenerateApi(params: {
  prompt?: string;
  messages?: ChatMessage[];
  model?: string;
  provider?: string;
}): Promise<ChatResponse> {
  const pickErrorMessage = (errorBody: unknown, status: number): string => {
    if (errorBody && typeof errorBody === 'object') {
      const body = errorBody as Record<string, unknown>;
      const detail = body.detail;
      if (typeof detail === 'string' && detail.trim()) return detail;
      if (detail && typeof detail === 'object') {
        const nested = detail as Record<string, unknown>;
        if (typeof nested.message === 'string' && nested.message.trim()) {
          return nested.message;
        }
        if (typeof nested.detail === 'string' && nested.detail.trim()) {
          return nested.detail;
        }
      }
      if (typeof body.error === 'string' && body.error.trim()) return body.error;
      if (typeof body.message === 'string' && body.message.trim()) return body.message;
    }
    return `Chat API returned ${status}`;
  };

  const normalizedModel =
    typeof params.model === 'string' && params.model.trim().length > 0
      ? params.model.trim()
      : undefined;
  const normalizedProvider =
    typeof params.provider === 'string' && params.provider.trim().length > 0
      ? params.provider.trim()
      : undefined;

  const res = await fetch('/api/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      prompt: params.prompt,
      messages: params.messages,
      // Leave model/provider unset unless user explicitly selected them.
      // This allows backend routing to pick the best model for the request.
      model: normalizedModel,
      provider: normalizedProvider,
    }),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(pickErrorMessage(errorBody, res.status));
  }

  return res.json();
}

export const chatClient = {
  async createConversation(
    params: CreateConversationParams = {}
  ): Promise<CreateConversationResult> {
    try {
      return await apiClient.createConversation(params.title);
    } catch (error) {
      throw new UiError(
        {
          code: 'CHAT_CONVERSATION_CREATE_FAILED',
          userMessage: 'We could not start a new conversation. Please try again.',
        },
        error
      );
    }
  },
  async sendMessage({
    conversationId,
    prompt,
    messages,
    model,
    provider,
  }: SendMessageParams): Promise<ChatResponse> {
    try {
      void conversationId;
      const hasExplicitSelection = Boolean(
        (typeof model === 'string' && model.trim()) ||
          (typeof provider === 'string' && provider.trim())
      );
      // Prefer same-origin Next.js proxy (no CORS issues). It will route to Fly backend first.
      try {
        return await callLocalGenerateApi({ prompt, messages, model, provider });
      } catch {
        // If explicit provider/model selection failed, retry once with backend auto-routing.
        if (hasExplicitSelection) {
          try {
            return await callLocalGenerateApi({ prompt, messages });
          } catch {
            // continue to legacy fallback below
          }
        }
        // Last resort: call the Fly backend directly (may be blocked by CORS depending on backend config).
        if (messages && messages.length > 0 && !prompt) {
          const lastUser = [...messages].reverse().find(m => m.role === 'user')?.content || '';
          return await apiClient.generate(lastUser, model);
        }
        return await apiClient.generate(prompt || '', model);
      }
    } catch (error) {
      throw new UiError(
        {
          code: 'CHAT_SEND_FAILED',
          userMessage: 'We could not send that message. Please try again.',
        },
        error
      );
    }
  },
};
