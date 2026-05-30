import {
  V1_CHAT_PREFIX,
  ConversationCreateResponse,
  ConversationInfoResponse,
  ConversationDetailResponse,
  ConversationSendResponse,
  postBackend,
  getBackend,
  withAuth,
  withTransientRetry,
  backendHttp,
} from './shared';
import type { ChatMessage as DomainChatMessage } from '../../domain/chat';

export const chatMethods = {
  async createConversation(title?: string) {
    const response = await withTransientRetry(
      () =>
        postBackend<ConversationCreateResponse, { title?: string }>(
          `${V1_CHAT_PREFIX}/conversations`,
          { title },
          withAuth()
        ),
      3,
      100
    );

    return {
      conversationId: response.conversation_id,
      title: response.title,
      createdAt: response.created_at,
    };
  },

  async listConversations() {
    const conversations = await getBackend<ConversationInfoResponse[]>(
      `${V1_CHAT_PREFIX}/conversations`,
      withAuth()
    );

    return conversations.map((conversation) => ({
      conversationId: conversation.conversation_id,
      title: conversation.title,
      snippet: conversation.snippet || '',
      createdAt: conversation.created_at,
      updatedAt: conversation.updated_at,
      messageCount: conversation.message_count,
    }));
  },

  async getConversation(conversationId: string, offset?: number, limit?: number) {
    const params = new URLSearchParams();
    if (typeof offset === 'number') params.append('offset', offset.toString());
    if (typeof limit === 'number') params.append('limit', limit.toString());

    const url = `${V1_CHAT_PREFIX}/conversations/${encodeURIComponent(conversationId)}${
      params.toString() ? `?${params.toString()}` : ''
    }`;

    const conversation = await getBackend<ConversationDetailResponse>(url, withAuth());

    return {
      conversationId: conversation.conversation_id,
      title: conversation.title,
      createdAt: conversation.created_at,
      updatedAt: conversation.updated_at,
      messages: conversation.messages.map((message) => ({
        id: message.message_id,
        createdAt: message.timestamp,
        role: message.role,
        content: message.content,
        meta:
          message.metadata && typeof message.metadata === 'object' ? message.metadata : undefined,
      })),
      pagination: (conversation as any)?.pagination,
    };
  },

  async sendConversationMessage(payload: {
    conversationId: string;
    message: string;
    model?: string;
    provider?: string;
    metadata?: Record<string, unknown>;
    attachment_ids?: string[];
  }) {
    const response = await postBackend<
      ConversationSendResponse,
      {
        message: string;
        model?: string;
        provider?: string;
        metadata?: Record<string, unknown>;
        attachment_ids?: string[];
      }
    >(
      `${V1_CHAT_PREFIX}/conversations/${encodeURIComponent(payload.conversationId)}/messages`,
      {
        message: payload.message,
        model: payload.model,
        provider: payload.provider,
        metadata: payload.metadata,
        attachment_ids: payload.attachment_ids,
      },
      withAuth()
    );

    return {
      messageId: response.message_id,
      content: response.response,
      provider: response.provider,
      model: response.model,
      createdAt: response.timestamp,
      usage: response.usage,
      cost_usd: response.cost_usd,
      correlation_id: response.correlation_id,
      visualizations: response.visualizations,
    };
  },

  async estimateMessageTokens(payload: {
    message: string;
    conversationId?: string;
    provider?: string;
    model?: string;
  }): Promise<{
    input_tokens: number;
    estimated_output_tokens: number;
    estimated_cost_usd: number;
    provider: string;
    model?: string;
    layers: Array<{ name: string; tokens: number }>;
    degraded_mode: boolean;
    degraded_reason?: string;
  }> {
    const qs = payload.conversationId
      ? `?conversation_id=${encodeURIComponent(payload.conversationId)}`
      : '';
    return postBackend(
      `${V1_CHAT_PREFIX}/estimate-tokens${qs}`,
      {
        message: payload.message,
        provider: payload.provider,
        model: payload.model,
      },
      withAuth()
    );
  },

  async importConversationMessages(conversationId: string, messages: DomainChatMessage[]) {
    return postBackend<{ success: boolean; imported_count: number }>(
      `${V1_CHAT_PREFIX}/conversations/${encodeURIComponent(conversationId)}/import`,
      {
        messages: messages.map((message) => ({
          role: message.role,
          content: message.content,
          metadata: message.meta,
          timestamp: message.createdAt,
        })),
      },
      withAuth()
    );
  },

  async uploadFile(file: File): Promise<{
    file_id: string;
    filename: string;
    mime_type: string;
    size_bytes: number;
  }> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await backendHttp.post(`${V1_CHAT_PREFIX}/upload-file`, formData, {
      ...withAuth(),
      headers: {
        ...withAuth().headers,
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },
};
