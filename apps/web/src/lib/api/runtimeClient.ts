import { providerKeys } from '@/lib/provider-keys';
import { env } from '@/config/env';
import { getAuthToken } from '@/utils/auth-session';
import type {
  CostSummary,
  GoblinStats,
  GoblinStatus,
  LoginResponse,
  MemoryEntry,
  OrchestrationPlan,
  ProviderModelOption,
  RuntimeClient,
  StreamChunk,
  TaskResponse,
  User,
} from '@/types/api';

import { apiClient } from '@/lib/api';

let runtimeConversationId: string | null = null;

const buildRuntimePrompt = (goblin: string, task: string, code?: string): string => {
  const sections = [`[goblin:${goblin}]`, task.trim()];
  if (code && code.trim()) {
    sections.push(`Code context:\n${code}`);
  }
  return sections.join('\n\n');
};

const ensureRuntimeConversation = async (): Promise<string> => {
  if (runtimeConversationId) return runtimeConversationId;
  const conversation = await apiClient.createConversation('Runtime Task Execution');
  runtimeConversationId = conversation.conversationId;
  return runtimeConversationId;
};

const runtimeClientImpl: RuntimeClient = {
  async getGoblins(): Promise<GoblinStatus[]> {
    return apiClient.getGoblins();
  },

  async getProviders(): Promise<string[]> {
    return apiClient.getProviders();
  },

  async getProviderModelOptions(provider: string): Promise<ProviderModelOption[]> {
    return apiClient.getProviderModelOptions(provider);
  },

  async getProviderModels(provider: string): Promise<string[]> {
    return apiClient.getProviderModels(provider);
  },

  async executeTask(
    goblin: string,
    task: string,
    _streaming?: boolean,
    code?: string,
    provider?: string,
    model?: string
  ): Promise<string> {
    const conversationId = await ensureRuntimeConversation();
    const prompt = buildRuntimePrompt(goblin, task, code);
    const response = await apiClient.sendConversationMessage({
      conversationId,
      message: prompt,
      provider,
      model,
      metadata: { source: 'runtime-client', goblin },
    });
    return response.content || '';
  },

  async executeTaskStreaming(
    goblin: string,
    task: string,
    onChunk: (chunk: StreamChunk) => void,
    onComplete?: (response: TaskResponse) => void,
    code?: string,
    provider?: string,
    model?: string
  ): Promise<void> {
    const conversationId = await ensureRuntimeConversation();
    const prompt = buildRuntimePrompt(goblin, task, code);
    const token = getAuthToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(`${env.apiBaseUrl}/v1/chat/stream`, {
      method: 'POST',
      headers,
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

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalResponse: TaskResponse | null = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines[lines.length - 1] || '';

      for (let i = 0; i < lines.length - 1; i++) {
        const line = lines[i]?.trim();
        if (!line || !line.startsWith('data: ')) continue;

        const payload = JSON.parse(line.slice(6)) as Record<string, unknown>;
        if (payload.type === 'error' || typeof payload.error === 'string') {
          const message =
            (typeof payload.message === 'string' && payload.message) ||
            (typeof payload.error === 'string' && payload.error) ||
            'Streaming failed';
          throw new Error(message);
        }

        const chunkContent =
          typeof payload.content === 'string'
            ? payload.content
            : typeof payload.result === 'string'
              ? payload.result
              : undefined;

        onChunk({
          content: chunkContent,
          done: payload.done === true,
          token_count: Number(payload.token_count) || undefined,
          cost_delta: Number(payload.cost_delta) || undefined,
          result: payload.result,
        });

        if (payload.done === true) {
          finalResponse = {
            result: payload.result,
            message_id: payload.message_id,
            provider: payload.provider,
            model: payload.model,
            tokens: payload.tokens,
            cost: payload.cost,
            duration_ms: payload.duration_ms,
            done: true,
          };
          onComplete?.(finalResponse);
          await reader.cancel();
          return;
        }
      }
    }

    if (!finalResponse) {
      onComplete?.({ result: { message: 'Stream closed without completion event.' } });
    }
  },

  async setProviderApiKey(provider: string, key: string): Promise<void> {
    providerKeys.set(provider, key);
  },

  async storeApiKey(provider: string, key: string): Promise<void> {
    providerKeys.set(provider, key);
  },

  async getApiKey(provider: string): Promise<string | null> {
    return providerKeys.get(provider);
  },

  async clearApiKey(provider: string): Promise<void> {
    providerKeys.remove(provider);
  },

  async getHistory(goblin: string, limit?: number): Promise<MemoryEntry[]> {
    return apiClient.getHistory(goblin, limit);
  },

  async getStats(goblin: string): Promise<GoblinStats> {
    return apiClient.getStats(goblin);
  },

  async getCostSummary(): Promise<CostSummary> {
    return apiClient.getCostSummary();
  },

  async parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan> {
    return apiClient.parseOrchestration(text, defaultGoblin);
  },

  async onTaskStream(): Promise<void> {},

  async login(email: string, password: string): Promise<LoginResponse> {
    return apiClient.login(email, password) as Promise<LoginResponse>;
  },

  async register(email: string, password: string): Promise<LoginResponse> {
    return apiClient.register(email, password) as Promise<LoginResponse>;
  },

  async logout(): Promise<void> {
    await apiClient.logout().catch(() => {});
  },

  async validateToken(token: string): Promise<{ valid: boolean; user?: User }> {
    const result = await apiClient.validateToken(token);
    return { valid: result?.valid ?? false, user: result?.user };
  },
};

export const runtimeClient = runtimeClientImpl;
export const runtimeClientDemo = runtimeClientImpl;
