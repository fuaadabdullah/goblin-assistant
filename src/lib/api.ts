import axios, { AxiosError, type AxiosRequestConfig } from 'axios';
import { env } from '../config/env';
import { devWarn } from '../utils/dev-log';
import { getAuthToken } from '../utils/auth-session';
import type { ChatMessage as DomainChatMessage, ChatUsage } from '../domain/chat';
import type {
  ChatMessage,
  ChatCompletionResponse,
  HealthStatus,
  ValidateTokenResponse,
} from '../types/api';

export interface ProviderUpdatePayload {
  name?: string;
  enabled?: boolean;
  priority?: number;
  weight?: number;
  api_key?: string;
  base_url?: string;
  models?: string[];
}

export interface PasskeyCredential {
  id: string;
  rawId: string;
  type: string;
  response: {
    attestationObject?: string;
    clientDataJSON: string;
    authenticatorData?: string;
    signature?: string;
  };
}

export interface SandboxRunPayload {
  code: string;
  language?: string;
  timeout?: number;
}

export interface AccountProfile {
  name?: string;
  email?: string;
  avatar_url?: string;
}

export interface AccountPreferences {
  theme?: string;
  default_model?: string;
  default_provider?: string;
  [key: string]: string | boolean | number | undefined;
}

interface ConversationCreateResponse {
  conversation_id: string;
  title: string;
  created_at: string;
}

interface ConversationInfoResponse {
  conversation_id: string;
  user_id?: string | null;
  title: string;
  message_count: number;
  snippet?: string | null;
  created_at: string;
  updated_at: string;
}

interface ConversationDetailResponse {
  conversation_id: string;
  user_id?: string | null;
  title: string;
  messages: Array<{
    message_id: string;
    role: DomainChatMessage['role'];
    content: string;
    timestamp: string;
    metadata?: DomainChatMessage['meta'];
  }>;
  created_at: string;
  updated_at: string;
  metadata?: Record<string, unknown>;
}

interface ConversationSendResponse {
  message_id: string;
  response: string;
  provider: string;
  model: string;
  timestamp: string;
  usage?: ChatUsage;
  cost_usd?: number;
  correlation_id?: string;
}

const backendHttp = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Used for same-origin Next.js API routes (e.g. /api/models, /api/generate)
const frontendHttp = axios.create({
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

const withAuth = (config?: AxiosRequestConfig): AxiosRequestConfig => {
  const token = getAuthToken();
  if (!token) return config ?? {};

  return {
    ...config,
    headers: {
      ...(config?.headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  };
};

const normalizeAxiosError = (error: unknown): never => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<Record<string, unknown>>;
    const payload = axiosError.response?.data;

    const detail =
      (typeof payload?.detail === 'string' && payload.detail) ||
      (typeof payload?.error === 'string' && payload.error) ||
      (typeof payload?.message === 'string' && payload.message) ||
      axiosError.message ||
      'Request failed';

    const normalizedError = new Error(detail) as Error & {
      status?: number;
      responseData?: Record<string, unknown>;
    };
    normalizedError.status = axiosError.response?.status;
    normalizedError.responseData = payload;

    throw normalizedError;
  }

  throw error instanceof Error ? error : new Error('Request failed');
};

const getBackend = async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  try {
    const response = await backendHttp.get<T>(url, config);
    return response.data;
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

const postBackend = async <T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig,
): Promise<T> => {
  try {
    const response = await backendHttp.post<T>(url, body, config);
    return response.data;
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

const putBackend = async <T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig,
): Promise<T> => {
  try {
    const response = await backendHttp.put<T>(url, body, config);
    return response.data;
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

const patchBackend = async <T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig,
): Promise<T> => {
  try {
    const response = await backendHttp.patch<T>(url, body, config);
    return response.data;
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

const getFrontend = async <T>(url: string, config?: AxiosRequestConfig): Promise<T> => {
  try {
    const response = await frontendHttp.get<T>(url, config);
    return response.data;
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

const postFrontend = async <T, B = unknown>(
  url: string,
  body?: B,
  config?: AxiosRequestConfig,
): Promise<T> => {
  try {
    const response = await frontendHttp.post<T>(url, body, config);
    return response.data;
  } catch (error) {
    return normalizeAxiosError(error);
  }
};

export const apiClient = {
  async createConversation(title?: string) {
    const response = await postBackend<ConversationCreateResponse, { title?: string }>(
      '/chat/conversations',
      { title },
      withAuth(),
    );

    return {
      conversationId: response.conversation_id,
      title: response.title,
      createdAt: response.created_at,
    };
  },

  async listConversations() {
    const conversations = await getBackend<ConversationInfoResponse[]>('/chat/conversations', withAuth());

    return conversations.map((conversation) => ({
      conversationId: conversation.conversation_id,
      title: conversation.title,
      snippet: conversation.snippet || '',
      createdAt: conversation.created_at,
      updatedAt: conversation.updated_at,
      messageCount: conversation.message_count,
    }));
  },

  async getConversation(conversationId: string) {
    const conversation = await getBackend<ConversationDetailResponse>(
      `/chat/conversations/${encodeURIComponent(conversationId)}`,
      withAuth(),
    );

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
          message.metadata && typeof message.metadata === 'object'
            ? message.metadata
            : undefined,
      })),
    };
  },

  async sendConversationMessage(payload: {
    conversationId: string;
    message: string;
    model?: string;
    provider?: string;
    metadata?: Record<string, unknown>;
  }) {
    const response = await postBackend<
      ConversationSendResponse,
      {
        message: string;
        model?: string;
        provider?: string;
        metadata?: Record<string, unknown>;
      }
    >(
      `/chat/conversations/${encodeURIComponent(payload.conversationId)}/messages`,
      {
        message: payload.message,
        model: payload.model,
        provider: payload.provider,
        metadata: payload.metadata,
      },
      withAuth(),
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
    };
  },

  async importConversationMessages(
    conversationId: string,
    messages: DomainChatMessage[],
  ) {
    return postBackend<{ success: boolean; imported_count: number }>(
      `/chat/conversations/${encodeURIComponent(conversationId)}/import`,
      {
        messages: messages.map((message) => ({
          role: message.role,
          content: message.content,
          metadata: message.meta,
          timestamp: message.createdAt,
        })),
      },
      withAuth(),
    );
  },

  async generate(prompt: string, model?: string) {
    return postFrontend('/api/generate', { prompt, model });
  },

  async chatCompletion(
    messages: ChatMessage[],
    model?: string,
    _streaming?: boolean,
  ) {
    const response = await postFrontend<ChatCompletionResponse & { content?: string }>(
      '/api/generate',
      { messages, model },
    );

    if (typeof response?.content === 'string') return response.content;
    const choice = response?.choices?.[0];
    return choice?.message?.content || response;
  },

  async getAllHealth(): Promise<HealthStatus> {
    try {
      return await getBackend<HealthStatus>('/health');
    } catch (error) {
      devWarn('Health check failed:', error);
      return {
        overall: 'unhealthy',
        timestamp: new Date().toISOString(),
        services: {},
      };
    }
  },

  async getStreamingHealth() {
    try {
      return await getBackend('/health/streaming');
    } catch (error) {
      devWarn('Streaming health check failed:', error);
      return { status: 'unknown' };
    }
  },

  async getRoutingHealth() {
    try {
      return await getBackend('/health/routing');
    } catch (error) {
      devWarn('Routing health check failed:', error);
      return { status: 'unknown' };
    }
  },

  async getRoutingInfo() {
    return getBackend('/routing/info');
  },

  async getProviderSettings() {
    return getBackend('/providers');
  },

  async getModelConfigs() {
    return getFrontend('/api/models');
  },

  async getGlobalSettings() {
    return getBackend('/settings');
  },

  async updateProvider(providerId: string | number, provider: ProviderUpdatePayload) {
    return patchBackend(`/providers/${providerId}`, provider);
  },

  async updateGlobalSetting(key: string, value: unknown) {
    return patchBackend(`/settings/${encodeURIComponent(key)}`, { value });
  },

  async setProviderPriority(
    providerId: number,
    priority: number,
    role?: string,
  ) {
    return postBackend(`/providers/${providerId}/priority`, { priority, role });
  },

  async reorderProviders(providerIds: number[]) {
    return postBackend('/providers/reorder', { providerIds });
  },

  async testProviderConnection(providerId: number | string) {
    return postBackend(`/providers/${providerId}/test`);
  },

  async testProviderWithPrompt(providerId: number | string, prompt: string) {
    return postBackend(`/providers/${providerId}/test-prompt`, { prompt });
  },

  async getRaptorLogs(limit = 100) {
    return getBackend(`/logs?limit=${limit}`);
  },

  async passkeyChallenge(email: string) {
    return postBackend('/auth/passkey/challenge', { email });
  },

  async passkeyRegister(email: string, credential: PasskeyCredential) {
    return postBackend('/auth/passkey/register', { email, credential });
  },

  async passkeyAuth(email: string, assertion: PasskeyCredential) {
    return postBackend('/auth/passkey/auth', { email, assertion });
  },

  async register(
    email: string,
    password: string,
    turnstileToken?: string | null,
  ) {
    return postBackend('/auth/register', { email, password, turnstileToken });
  },

  async login(email: string, password: string) {
    return postBackend('/auth/login', { email, password });
  },

  async validateToken(token: string): Promise<ValidateTokenResponse> {
    return postFrontend<ValidateTokenResponse>(
      '/api/auth/validate',
      {},
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      },
    );
  },

  async logout() {
    return postBackend('/auth/logout', undefined, withAuth());
  },

  async getGoogleAuthUrl() {
    return getBackend('/auth/google/url');
  },

  async getSearchCollections() {
    return getBackend('/search/collections');
  },

  async searchQuery(collection: string, query: string, limit = 8) {
    return postBackend('/search/query', { collection, query, limit });
  },

  async getSandboxJobs() {
    return getBackend('/sandbox/jobs');
  },

  async getJobLogs(jobId: string) {
    return getBackend(`/sandbox/jobs/${jobId}/logs`);
  },

  async runSandboxCode(payload: SandboxRunPayload) {
    return postBackend('/sandbox/run', payload);
  },

  async sendSupportMessage(message: string) {
    return postBackend('/support/message', { message });
  },

  async saveAccountProfile(payload: AccountProfile) {
    return putBackend('/account/profile', payload);
  },

  async saveAccountPreferences(payload: AccountPreferences) {
    return putBackend('/account/preferences', payload);
  },
};
