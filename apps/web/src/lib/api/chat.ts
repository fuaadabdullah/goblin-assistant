import {
  V1_API_PREFIX,
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
        postBackend<ConversationCreateResponse, { title?: string | undefined }>(
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
      ...(conversation.category ? { category: conversation.category } : {}),
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
      pagination: conversation.pagination,
    };
  },

  async sendConversationMessage(payload: {
    conversationId: string;
    message: string;
    department?: string | undefined;
    model?: string | undefined;
    provider?: string | undefined;
    metadata?: Record<string, unknown> | undefined;
    attachment_ids?: string[] | undefined;
  }) {
    const response = await postBackend<
      ConversationSendResponse,
      {
        message: string;
        department?: string | undefined;
        model?: string | undefined;
        provider?: string | undefined;
        metadata?: Record<string, unknown> | undefined;
        attachment_ids?: string[] | undefined;
      }
    >(
      `${V1_CHAT_PREFIX}/conversations/${encodeURIComponent(payload.conversationId)}/messages`,
      {
        message: payload.message,
        department: payload.department,
        model: payload.model,
        provider: payload.provider,
        metadata: payload.metadata,
        attachment_ids: payload.attachment_ids,
      },
      withAuth()
    );

    return {
      messageId: response.message_id,
      content:
        typeof response.response === 'string'
          ? response.response
          : JSON.stringify(response.response),
      department: (response as any).department || 'general',
      department_reason: (response as any).department_reason || '',
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
    conversationId?: string | undefined;
    provider?: string | undefined;
    model?: string | undefined;
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

  async submitRoutingFeedback(payload: {
    requestId: string;
    rating?: 1 | -1;
    signal?: string;
    providerId?: string;
    taskType?: string;
    messageId?: string;
    conversationId?: string;
    model?: string;
    department?: string;
  }): Promise<{ ok: boolean }> {
    return postBackend<{ ok: boolean }, object>(
      `${V1_API_PREFIX}/routing/feedback`,
      {
        request_id: payload.requestId,
        rating: payload.rating,
        signal: payload.signal,
        provider_id: payload.providerId,
        task_type: payload.taskType,
        message_id: payload.messageId,
        conversation_id: payload.conversationId,
        model: payload.model,
        department: payload.department,
      },
      withAuth()
    );
  },

  async getFeedbackStats(days: number = 7): Promise<{
    total_events: number;
    thumbs_up_count: number;
    thumbs_down_count: number;
    regenerate_count: number;
    delete_count: number;
    continue_count: number;
    copy_count: number;
    provider_switch_count: number;
    model_switch_count: number;
    thumbs_up_rate: number;
    by_department: Record<string, { thumbs_up: number; thumbs_down: number; total: number }>;
    by_provider: Record<string, { thumbs_up: number; thumbs_down: number; total: number }>;
    recent_events: Array<{
      event_id: string;
      signal: string;
      rating: number | null;
      user_id: string;
      department: string | null;
      provider: string | null;
      model: string | null;
      task_type: string | null;
      created_at: string | null;
    }>;
  }> {
    return getBackend(`${V1_API_PREFIX}/feedback/stats?days=${days}`, withAuth());
  },
};
