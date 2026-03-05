import { env } from "../config/env";
import { devWarn } from "../utils/dev-log";
import type {
  ChatMessage,
  ChatCompletionResponse,
  HealthStatus,
} from "../types/api";

// Typed payload interfaces for API methods
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

const API_BASE = env.apiBaseUrl;

const jsonHeaders = {
  "Content-Type": "application/json",
};

const safeParseJson = async (res: Response) => {
  try {
    return await res.json();
  } catch {
    return null;
  }
};

const requestJson = async <T>(url: string, init?: RequestInit): Promise<T> => {
  const res = await fetch(url, init);
  if (!res.ok) {
    const payload = await safeParseJson(res);
    const detail =
      payload?.detail || payload?.error || `Request failed with ${res.status}`;
    throw new Error(detail);
  }
  return (await safeParseJson(res)) as T;
};

const buildBackendUrl = (path: string) => {
  if (path.startsWith("http")) return path;
  if (path.startsWith("/")) return `${API_BASE}${path}`;
  return `${API_BASE}/${path}`;
};

const localConversationId = () => {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `conv-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
};

export const apiClient = {
  async createConversation(title?: string) {
    return {
      conversationId: localConversationId(),
      title: title || "New chat",
      createdAt: new Date().toISOString(),
    };
  },

  async generate(prompt: string, model?: string) {
    return requestJson("/api/generate", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ prompt, model }),
    });
  },

  async chatCompletion(
    messages: ChatMessage[],
    model?: string,
    _streaming?: boolean,
  ) {
    const response = await requestJson<
      ChatCompletionResponse & { content?: string }
    >("/api/generate", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ messages, model }),
    });

    if (typeof response?.content === "string") return response.content;
    const choice = (response as ChatCompletionResponse)?.choices?.[0];
    return choice?.message?.content || response;
  },

  async getAllHealth(): Promise<HealthStatus> {
    try {
      return await requestJson(buildBackendUrl("/v1/health"), {
        method: "GET",
      });
    } catch (error) {
      devWarn("Health check failed:", error);
      return {
        overall: "unhealthy",
        timestamp: new Date().toISOString(),
        services: {},
      };
    }
  },

  async getStreamingHealth() {
    try {
      return await requestJson(buildBackendUrl("/v1/health/streaming"), {
        method: "GET",
      });
    } catch (error) {
      devWarn("Streaming health check failed:", error);
      return { status: "unknown" };
    }
  },

  async getRoutingHealth() {
    try {
      return await requestJson(buildBackendUrl("/v1/health/routing"), {
        method: "GET",
      });
    } catch (error) {
      devWarn("Routing health check failed:", error);
      return { status: "unknown" };
    }
  },

  async getRoutingInfo() {
    return requestJson(buildBackendUrl("/v1/routing/info"), {
      method: "GET",
    });
  },

  async getProviderSettings() {
    return requestJson(buildBackendUrl("/v1/providers"), {
      method: "GET",
    });
  },

  async getModelConfigs() {
    return requestJson("/api/models", {
      method: "GET",
    });
  },

  async getGlobalSettings() {
    return requestJson(buildBackendUrl("/v1/settings"), {
      method: "GET",
    });
  },

  async updateProvider(providerId: string | number, provider: ProviderUpdatePayload) {
    return requestJson(buildBackendUrl(`/v1/providers/${providerId}`), {
      method: "PATCH",
      headers: jsonHeaders,
      body: JSON.stringify(provider),
    });
  },

  async updateGlobalSetting(key: string, value: unknown) {
    return requestJson(
      buildBackendUrl(`/v1/settings/${encodeURIComponent(key)}`),
      {
        method: "PATCH",
        headers: jsonHeaders,
        body: JSON.stringify({ value }),
      },
    );
  },

  async setProviderPriority(
    providerId: number,
    priority: number,
    role?: string,
  ) {
    return requestJson(
      buildBackendUrl(`/v1/providers/${providerId}/priority`),
      {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ priority, role }),
      },
    );
  },

  async reorderProviders(providerIds: number[]) {
    return requestJson(buildBackendUrl("/v1/providers/reorder"), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ providerIds }),
    });
  },

  async testProviderConnection(providerId: number | string) {
    return requestJson(buildBackendUrl(`/v1/providers/${providerId}/test`), {
      method: "POST",
    });
  },

  async testProviderWithPrompt(providerId: number | string, prompt: string) {
    return requestJson(
      buildBackendUrl(`/v1/providers/${providerId}/test-prompt`),
      {
        method: "POST",
        headers: jsonHeaders,
        body: JSON.stringify({ prompt }),
      },
    );
  },

  async getRaptorLogs(limit = 100) {
    return requestJson(buildBackendUrl(`/v1/logs?limit=${limit}`), {
      method: "GET",
    });
  },

  async passkeyChallenge(email: string) {
    return requestJson(buildBackendUrl("/v1/auth/passkey/challenge"), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ email }),
    });
  },

  async passkeyRegister(email: string, credential: PasskeyCredential) {
    return requestJson(buildBackendUrl("/v1/auth/passkey/register"), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ email, credential }),
    });
  },

  async passkeyAuth(email: string, assertion: PasskeyCredential) {
    return requestJson(buildBackendUrl("/v1/auth/passkey/auth"), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ email, assertion }),
    });
  },

  async register(
    email: string,
    password: string,
    turnstileToken?: string | null,
  ) {
    return requestJson(buildBackendUrl("/v1/auth/register"), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ email, password, turnstileToken }),
    });
  },

  async login(email: string, password: string) {
    return requestJson(buildBackendUrl("/v1/auth/login"), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ email, password }),
    });
  },

  async getGoogleAuthUrl() {
    return requestJson(buildBackendUrl("/v1/auth/google/url"), {
      method: "GET",
    });
  },

  async getSearchCollections() {
    return requestJson(buildBackendUrl("/v1/search/collections"), {
      method: "GET",
    });
  },

  async searchQuery(collection: string, query: string, limit = 8) {
    return requestJson(buildBackendUrl("/v1/search/query"), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ collection, query, limit }),
    });
  },

  async getSandboxJobs() {
    return requestJson(buildBackendUrl("/v1/sandbox/jobs"), { method: "GET" });
  },

  async getJobLogs(jobId: string) {
    return requestJson(buildBackendUrl(`/v1/sandbox/jobs/${jobId}/logs`), {
      method: "GET",
    });
  },

  async runSandboxCode(payload: SandboxRunPayload) {
    return requestJson(buildBackendUrl("/v1/sandbox/run"), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
  },

  async sendSupportMessage(message: string) {
    return requestJson(buildBackendUrl("/v1/support/message"), {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ message }),
    });
  },

  async saveAccountProfile(payload: AccountProfile) {
    return requestJson(buildBackendUrl("/v1/account/profile"), {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
  },

  async saveAccountPreferences(payload: AccountPreferences) {
    return requestJson(buildBackendUrl("/v1/account/preferences"), {
      method: "PUT",
      headers: jsonHeaders,
      body: JSON.stringify(payload),
    });
  },
};
