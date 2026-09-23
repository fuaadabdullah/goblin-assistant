import { apiClient } from '@/lib/api';
import { UiError } from '../../../lib/ui-error';
import type { ChatMessage } from '../types';

export interface ChatResponse {
  messageId?: string | undefined;
  content?: string | undefined;
  department?: string | undefined; // Which brain department handled this
  department_reason?: string | undefined; // Why this department was chosen
  model?: string | undefined; // Deprecated: internal
  provider?: string | undefined; // Deprecated: internal
  usage?:
    | {
        input_tokens?: number | undefined;
        output_tokens?: number | undefined;
        total_tokens?: number | undefined;
      }
    | undefined;
  cost_usd?: number | undefined;
  correlation_id?: string | undefined;
  createdAt?: string | undefined;
  visualizations?:
    | Array<{
        type: string;
        title: string;
        data: Record<string, unknown>[];
        config: Record<string, unknown>;
      }>
    | undefined;
}

export interface FileUploadResult {
  file_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
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
  category?: string;
}

export interface ChatConversation {
  conversationId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
  // Mirrors the backend ConversationDetailResponse pagination, whose fields are all optional.
  pagination?:
    | {
        offset?: number | undefined;
        limit?: number | undefined;
        total?: number | undefined;
        returned?: number | undefined;
        has_more?: boolean | undefined;
      }
    | undefined;
}

export interface SendMessageParams {
  conversationId: string;
  prompt?: string | undefined;
  messages?: ChatMessage[] | undefined;
  department?: string | undefined; // e.g. "reasoning", "coding", "creative", "research"
  mode?: string | undefined; // e.g. "GENERAL_ASSISTANT", "DEEP_RESEARCH", "DEBUG"
  model?: string | undefined; // Deprecated: use department instead
  provider?: string | undefined; // Deprecated: use department instead
  attachment_ids?: string[] | undefined;
}

const resolvePrompt = (params: SendMessageParams): string => {
  if (typeof params.prompt === 'string' && params.prompt.trim()) {
    return params.prompt.trim();
  }

  const lastUser = [...(params.messages || [])]
    .reverse()
    .find((message) => message.role === 'user');
  return lastUser?.content?.trim() || '';
};

const getErrorStatus = (error: unknown): number | undefined => {
  if (!error || typeof error !== 'object') return undefined;

  const candidate = error as { status?: unknown; response?: { status?: unknown } };
  const status = candidate.status ?? candidate.response?.status;
  return typeof status === 'number' ? status : undefined;
};

export const chatClient = {
  async createConversation(
    params: CreateConversationParams = {}
  ): Promise<CreateConversationResult> {
    try {
      return await apiClient.createConversation(params.title);
    } catch (error) {
      const status = getErrorStatus(error);
      if (status === 401 || status === 403) {
        throw new UiError(
          {
            code: 'AUTHENTICATION_REQUIRED',
            userMessage: 'You need to sign in to start a conversation.',
          },
          error
        );
      }

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

  async getConversation(
    conversationId: string,
    params?: { offset?: number; limit?: number }
  ): Promise<ChatConversation> {
    try {
      return await apiClient.getConversation(conversationId, params?.offset, params?.limit);
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

  async estimateTokens(payload: {
    message: string;
    conversationId?: string | undefined;
    provider?: string | undefined;
    model?: string | undefined;
  }) {
    return apiClient.estimateMessageTokens(payload);
  },

  async chatCompletion(messages: ChatMessage[], model?: string) {
    return apiClient.chatCompletion(messages, model);
  },

  async uploadFile(file: File): Promise<FileUploadResult> {
    return apiClient.uploadFile(file);
  },

  async sendMessage({
    conversationId,
    prompt,
    messages,
    department,
    mode,
    model,
    provider,
    attachment_ids,
  }: SendMessageParams): Promise<ChatResponse> {
    const resolvedPrompt = resolvePrompt({ conversationId, prompt, messages, model, provider });
    try {
      if (!resolvedPrompt) {
        throw new Error('Conversation message is required.');
      }

      const hasExplicitSelection = Boolean(
        (typeof model === 'string' && model.trim()) ||
        (typeof provider === 'string' && provider.trim()) ||
        (typeof department === 'string' && department.trim())
      );

      try {
        return await apiClient.sendConversationMessage({
          conversationId,
          message: resolvedPrompt,
          department,
          mode,
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
      const backendError =
        errorObj?.responseData?.error ||
        errorObj?.response?.data?.error ||
        errorObj?.response?.data?.detail ||
        errorObj?.response?.data?.message;

      if (backendError === 'provider-access-denied') {
        throw new UiError(
          {
            code: 'CHAT_PROVIDER_ACCESS_DENIED',
            userMessage: 'Your account does not have access to any providers right now.',
          },
          error
        );
      }

      if (backendError === 'no-configured-providers') {
        throw new UiError(
          {
            code: 'CHAT_PROVIDER_UNAVAILABLE',
            userMessage: 'No providers are configured right now. Please try again later.',
          },
          error
        );
      }

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
};
