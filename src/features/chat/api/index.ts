import { apiClient } from '@/api';
import { UiError } from '../../../lib/ui-error';
import { getAuthToken } from '../../../utils/auth-session';
import type { ChatMessage } from '../types';

export interface ChatResponse {
  messageId?: string;
  content?: string;
  model?: string;
  provider?: string;
  usage?: { input_tokens?: number; output_tokens?: number; total_tokens?: number };
  cost_usd?: number;
  correlation_id?: string;
  createdAt?: string;
  visualizations?: Array<{
    type: string;
    title: string;
    data: Record<string, unknown>[];
    config: Record<string, unknown>;
  }>;
}

export interface CreateConversationParams {
  title?: string;
}

export interface CreateConversationResult {
  conversationId: string;
  title?: string;
  createdAt: string;
}

export interface ChatConversationSummary {
  conversationId: string;
  title: string;
  snippet: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
}

export interface ChatConversation {
  conversationId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface SendMessageParams {
  conversationId: string;
  prompt?: string;
  messages?: ChatMessage[];
  model?: string;
  provider?: string;
  attachment_ids?: string[];
}

const resolvePrompt = (params: SendMessageParams): string => {
  if (typeof params.prompt === 'string' && params.prompt.trim()) {
    return params.prompt.trim();
  }

  const lastUser = [...(params.messages || [])].reverse().find(message => message.role === 'user');
  return lastUser?.content?.trim() || '';
};

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

  async listConversations(): Promise<ChatConversationSummary[]> {
    try {
      return await apiClient.listConversations();
    } catch (error) {
      throw new UiError(
        {
          code: 'CHAT_THREADS_LOAD_FAILED',
          userMessage: 'We could not load your conversations right now.',
        },
        error
      );
    }
  },

  async getConversation(conversationId: string): Promise<ChatConversation> {
    try {
      return await apiClient.getConversation(conversationId);
    } catch (error) {
      throw new UiError(
        {
          code: 'CHAT_CONVERSATION_LOAD_FAILED',
          userMessage: 'We could not load that conversation right now.',
        },
        error
      );
    }
  },

  async importConversationMessages(conversationId: string, messages: ChatMessage[]): Promise<void> {
    try {
      await apiClient.importConversationMessages(conversationId, messages);
    } catch (error) {
      throw new UiError(
        {
          code: 'CHAT_CONVERSATION_IMPORT_FAILED',
          userMessage: 'We could not continue that older conversation right now.',
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
    attachment_ids,
  }: SendMessageParams): Promise<ChatResponse> {
    try {
      const resolvedPrompt = resolvePrompt({ conversationId, prompt, messages, model, provider });
      if (!resolvedPrompt) {
        throw new Error('Conversation message is required.');
      }

      const hasExplicitSelection = Boolean(
        (typeof model === 'string' && model.trim()) ||
          (typeof provider === 'string' && provider.trim())
      );

      try {
        return await apiClient.sendConversationMessage({
          conversationId,
          message: resolvedPrompt,
          model,
          provider,
          attachment_ids,
        });
      } catch (error) {
        if (!hasExplicitSelection) {
          throw error;
        }

        return await apiClient.sendConversationMessage({
          conversationId,
          message: resolvedPrompt,
          attachment_ids,
        });
      }
    } catch (error) {
      // Check for specific error statuses
      const errorObj = error as any;
      const status = errorObj?.response?.status || errorObj?.status;
      
      if (status === 413) {
        throw new UiError(
          {
            code: 'MESSAGE_TOO_LONG',
            userMessage: 'Your message is too long. Please keep messages under 10,000 characters.',
          },
          error
        );
      }
      
      if (status === 401 || status === 403) {
        throw new UiError(
          {
            code: 'AUTHENTICATION_REQUIRED',
            userMessage: 'You need to sign in to send messages.',
          },
          error
        );
      }
      
      throw new UiError(
        {
          code: 'CHAT_SEND_FAILED',
          userMessage: 'We could not send that message. Please try again.',
        },
        error
      );
    }
  },

  async sendMessageStreaming({
    conversationId,
    prompt,
    messages,
    model,
    provider,
    onChunk,
    onComplete,
    onError,
  }: SendMessageParams & {
    onChunk: (content: string, token_count: number, cost_delta: number) => void;
    onComplete: (response: ChatResponse) => void;
    onError: (error: Error) => void;
  }): Promise<void> {
    try {
      const resolvedPrompt = resolvePrompt({ conversationId, prompt, messages, model, provider });
      if (!resolvedPrompt) {
        throw new Error('Conversation message is required.');
      }

      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 
        (typeof window !== 'undefined' ? '' : 'http://localhost:8000');
      const token = getAuthToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const streamUrl = `${apiBaseUrl}/chat/stream`;

      const response = await fetch(streamUrl, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          conversation_id: conversationId,
          message: resolvedPrompt,
          model,
          provider,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('Response body is empty');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedContent = '';
      let totalTokens = 0;
      let totalCost = 0;

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines[lines.length - 1];

          for (let i = 0; i < lines.length - 1; i++) {
            const line = lines[i].trim();
            if (!line || line.startsWith(':')) continue;

            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.content) {
                  accumulatedContent += data.content;
                  const tokenCount = data.token_count || 0;
                  const costDelta = data.cost_delta || 0;
                  totalTokens += tokenCount;
                  totalCost += costDelta;
                  onChunk(data.content, tokenCount, costDelta);
                }

                if (data.done === true) {
                  // Final message with full response
                  const finalResponse: ChatResponse = {
                    messageId: data.message_id,
                    content: data.result || accumulatedContent,
                    provider: data.provider,
                    model: data.model,
                    usage: {
                      total_tokens: data.tokens ?? totalTokens,
                      input_tokens: data.usage?.input_tokens,
                      output_tokens: data.usage?.output_tokens,
                    },
                    cost_usd: data.cost ?? totalCost,
                    correlation_id: data.correlation_id,
                    createdAt: data.timestamp,
                    visualizations: data.visualizations,
                  };
                  onComplete(finalResponse);
                  reader.cancel();
                  return;
                }
              } catch (err) {
                // Continue on parse error
              }
            }
          }
        }

        // If we got here without hitting done, treat as complete
        const finalResponse: ChatResponse = {
          content: accumulatedContent,
          cost_usd: totalCost,
        };
        onComplete(finalResponse);
      } catch (err) {
        reader.cancel();
        throw err;
      }
    } catch (error) {
      const uiError = error instanceof Error 
        ? error 
        : new Error('Unknown error during streaming');
      onError(uiError);
      throw new UiError(
        {
          code: 'CHAT_STREAM_FAILED',
          userMessage: 'The connection was interrupted. Please try again.',
        },
        error
      );
    }
  },
};
