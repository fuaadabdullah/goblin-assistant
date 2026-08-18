import type { Page, Route } from '@playwright/test';
import { mockCommonApiRoutes } from './common-mocks';

export type ServiceState = 'ok' | 'degraded' | 'down' | 'unknown';

export type CapturedRequest = {
  url: string;
  method: string;
  body: Record<string, unknown>;
};

export type RouteOutcome = {
  status: number;
  body: unknown;
  contentType?: string;
  headers?: Record<string, string>;
  delayMs?: number;
};

export type ConversationMessage = {
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
};

export type ConversationRecord = {
  conversation_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
  metadata?: Record<string, unknown>;
};

type SendResponderContext = {
  requestBody: Record<string, unknown>;
  requestIndex: number;
  conversationId: string;
  conversation: ConversationRecord;
};

type CreateResponderContext = {
  requestBody: Record<string, unknown>;
  requestIndex: number;
};

const NOW_ISO = '2026-08-18T12:00:00.000Z';

const DEFAULT_MODELS_RESPONSE = {
  providers: [
    {
      id: 'openai',
      name: 'OpenAI',
      enabled: true,
      configured: true,
      health: 'healthy',
      status: 'healthy',
      models: ['gpt-4o-mini'],
    },
    {
      id: 'anthropic',
      name: 'Anthropic',
      enabled: true,
      configured: true,
      health: 'healthy',
      status: 'healthy',
      models: ['claude-3-haiku'],
    },
  ],
  models: [
    {
      provider: 'openai',
      name: 'gpt-4o-mini',
      is_selectable: true,
      health: 'healthy',
      health_reason: null,
    },
    {
      provider: 'anthropic',
      name: 'claude-3-haiku',
      is_selectable: true,
      health: 'healthy',
      health_reason: null,
    },
  ],
  total_providers: 2,
  total_models: 2,
};

const DEFAULT_SYSTEM_STATUS = {
  models: 'ok' as ServiceState,
  routing: 'ok' as ServiceState,
  sandbox: 'ok' as ServiceState,
  updatedAt: NOW_ISO,
};

const DEFAULT_PROVIDER_SETTINGS = [
  {
    id: 1,
    name: 'openai',
    enabled: true,
    configured: true,
    models: ['gpt-4o-mini'],
  },
  {
    id: 2,
    name: 'anthropic',
    enabled: true,
    configured: true,
    models: ['claude-3-haiku'],
  },
];

const DEFAULT_HEALTH = {
  overall: 'healthy',
  status: 'healthy',
  latency_ms: 42,
  last_check: NOW_ISO,
  components: {
    api: { status: 'healthy' },
    routing: { status: 'healthy' },
    database: { status: 'healthy' },
    redis: { status: 'healthy' },
    cache: { status: 'healthy' },
  },
  services: {
    api: { status: 'healthy' },
    routing: { status: 'healthy' },
    database: { status: 'healthy' },
    redis: { status: 'healthy' },
    cache: { status: 'healthy' },
  },
};

const DEFAULT_ACCOUNT_PREFERENCES = {
  default_provider: 'openai',
  default_model: 'gpt-4o-mini',
};

const parseRequestBody = (body: unknown): Record<string, unknown> => {
  if (!body || typeof body !== 'object') {
    return {};
  }
  return body as Record<string, unknown>;
};

const readPostData = (route: Route): Record<string, unknown> => {
  try {
    return parseRequestBody(route.request().postDataJSON());
  } catch {
    return {};
  }
};

const createConversationMessage = (
  role: 'user' | 'assistant',
  content: string,
  messageIndex: number,
  metadata?: Record<string, unknown>
): ConversationMessage => ({
  message_id: `${role}-${String(messageIndex).padStart(4, '0')}`,
  role,
  content,
  timestamp: NOW_ISO,
  ...(metadata ? { metadata } : {}),
});

const deriveSnippet = (messages: ConversationMessage[]): string => {
  const lastAssistant = [...messages].reverse().find((message) => message.role === 'assistant');
  return lastAssistant?.content || messages[messages.length - 1]?.content || '';
};

const summarizeConversation = (record: ConversationRecord) => ({
  conversation_id: record.conversation_id,
  title: record.title,
  snippet: deriveSnippet(record.messages),
  created_at: record.created_at,
  updated_at: record.updated_at,
  message_count: record.messages.length,
});

const buildDetail = (record: ConversationRecord) => ({
  conversation_id: record.conversation_id,
  title: record.title,
  created_at: record.created_at,
  updated_at: record.updated_at,
  messages: record.messages,
  pagination: {
    offset: 0,
    limit: 50,
    total: record.messages.length,
    returned: record.messages.length,
    has_more: false,
  },
});

const defaultAssistantReply = (prompt: string): string => {
  if (/what do you remember|recall/i.test(prompt)) {
    return 'You prefer blunt answers.';
  }
  if (/remember/i.test(prompt)) {
    return 'Memory saved as a durable fact.';
  }
  if (/tool|search/i.test(prompt)) {
    return 'Tool executed: web_search returned current context.';
  }
  if (/rate limit/i.test(prompt)) {
    return 'Retry after the current limit window.';
  }
  if (/huge conversation/i.test(prompt)) {
    return 'Huge conversation loaded and preserved.';
  }
  return 'Streaming response complete.';
};

const defaultChatUsage = {
  input_tokens: 8,
  output_tokens: 12,
  total_tokens: 20,
};

export function createBrutalHarness(page: Page) {
  const captured: CapturedRequest[] = [];
  const conversations = new Map<string, ConversationRecord>();
  let nextConversationIndex = 1;
  let nextMessageIndex = 1;

  let providerSettings = DEFAULT_PROVIDER_SETTINGS.map((provider) => ({ ...provider }));
  let modelsResponse = structuredClone(DEFAULT_MODELS_RESPONSE);
  let systemStatus = { ...DEFAULT_SYSTEM_STATUS };
  let healthResponse = structuredClone(DEFAULT_HEALTH);
  let accountPreferences = { ...DEFAULT_ACCOUNT_PREFERENCES };
  let sandboxJobsResponse: unknown = { jobs: [] };
  let sandboxRunResponse: RouteOutcome = {
    status: 200,
    body: { output: 'sandbox-result: 42', job_id: 'job-critical' },
  };
  let authValidateResponse: RouteOutcome = {
    status: 200,
    body: {
      valid: true,
      user: { id: 'test_user', email: 'test@example.com', role: 'user' },
      expires_in: 3600,
    },
  };
  let registerResponse: RouteOutcome = {
    status: 200,
    body: {
      access_token: 'mock-access-token-e2e',
      refresh_token: 'mock-refresh-token-e2e',
      token_type: 'bearer',
      expires_in: 3600,
      user: { id: 'new-user', email: 'new-user@example.com', role: 'user' },
    },
  };
  let loginResponse: RouteOutcome = registerResponse;
  let createConversationResponder: (
    ctx: CreateResponderContext
  ) => Promise<RouteOutcome> | RouteOutcome = ({ requestBody, requestIndex }) => ({
    status: 200,
    body: {
      conversation_id: `conv-brutal-${String(requestIndex).padStart(3, '0')}`,
      title: String(requestBody.title || 'New critical journey chat'),
      created_at: NOW_ISO,
    },
  });
  let sendMessageResponder: (
    ctx: SendResponderContext
  ) => Promise<RouteOutcome> | RouteOutcome = ({ requestBody, conversationId, conversation }) => {
    const prompt = String(requestBody.message || requestBody.prompt || '');
    const content = defaultAssistantReply(prompt);

    const record = conversation;
    record.messages.push(
      createConversationMessage('user', prompt, nextMessageIndex++)
    );
    const assistantMetadata = {
      provider: String(requestBody.provider || 'openai'),
      model: String(requestBody.model || 'gpt-4o-mini'),
      usage: defaultChatUsage,
      cost_usd: 0.0002,
      correlation_id: `corr-${String(nextMessageIndex).padStart(4, '0')}`,
    };
    record.messages.push(
      createConversationMessage('assistant', content, nextMessageIndex++, assistantMetadata)
    );
    record.updated_at = NOW_ISO;
    conversations.set(conversationId, record);

    return {
      status: 200,
      body: {
        message_id: record.messages[record.messages.length - 1].message_id,
        response: content,
        provider: String(requestBody.provider || 'openai'),
        model: String(requestBody.model || 'gpt-4o-mini'),
        timestamp: NOW_ISO,
        usage: defaultChatUsage,
        cost_usd: 0.0002,
        correlation_id: assistantMetadata.correlation_id,
      },
    };
  };

  const fulfillJson = async (route: Route, outcome: RouteOutcome) => {
    if (outcome.delayMs) {
      await new Promise((resolve) => setTimeout(resolve, outcome.delayMs));
    }

    const body =
      typeof outcome.body === 'string' ? outcome.body : JSON.stringify(outcome.body);

    await route.fulfill({
      status: outcome.status,
      contentType: outcome.contentType || 'application/json',
      headers: outcome.headers,
      body,
    });
  };

  const applyAuthCookies = async (body: unknown) => {
    if (!body || typeof body !== 'object') {
      return;
    }

    const record = body as Record<string, unknown>;
    const accessToken = typeof record.access_token === 'string' ? record.access_token : null;
    const refreshToken = typeof record.refresh_token === 'string' ? record.refresh_token : null;
    const user = record.user && typeof record.user === 'object' ? (record.user as Record<string, unknown>) : null;

    if (!accessToken) {
      return;
    }

    const cookies = [
      {
        name: 'session_token',
        value: accessToken,
        domain: 'localhost',
        path: '/',
      },
      {
        name: 'goblin_auth',
        value: '1',
        domain: 'localhost',
        path: '/',
      },
      {
        name: 'goblin_e2e_auth',
        value: '1',
        domain: 'localhost',
        path: '/',
      },
    ];

    if (refreshToken) {
      cookies.push({
        name: 'refresh_token',
        value: refreshToken,
        domain: 'localhost',
        path: '/',
      });
    }

    cookies.push({
      name: 'goblin_admin',
      value: user?.role === 'admin' ? '1' : '0',
      domain: 'localhost',
      path: '/',
    });

    await page.context().addCookies(cookies);
  };

  const install = async () => {
    await mockCommonApiRoutes(page);

    await page.route('**/auth/csrf-token', async (route) => {
      await fulfillJson(route, { status: 200, body: { csrf_token: 'csrf-brutal' } });
    });

    await page.route('**/api/auth/csrf-token', async (route) => {
      await fulfillJson(route, { status: 200, body: { csrf_token: 'csrf-brutal' } });
    });

    await page.route('**/api/auth/validate', async (route) => {
      const body = readPostData(route);
      captured.push({
        url: route.request().url(),
        method: route.request().method(),
        body,
      });
      await fulfillJson(route, authValidateResponse);
    });

    await page.route('**/auth/register', async (route) => {
      const body = readPostData(route);
      captured.push({
        url: route.request().url(),
        method: route.request().method(),
        body,
      });
      if (registerResponse.status >= 200 && registerResponse.status < 300) {
        await applyAuthCookies(registerResponse.body);
      }
      await fulfillJson(route, registerResponse);
    });

    await page.route('**/auth/login', async (route) => {
      const body = readPostData(route);
      captured.push({
        url: route.request().url(),
        method: route.request().method(),
        body,
      });
      if (loginResponse.status >= 200 && loginResponse.status < 300) {
        await applyAuthCookies(loginResponse.body);
      }
      await fulfillJson(route, loginResponse);
    });

    await page.route('**/api/models*', async (route) => {
      if (route.request().method() !== 'GET') {
        await route.continue();
        return;
      }

      await fulfillJson(route, { status: 200, body: modelsResponse });
    });

    await page.route('**/api/system-status*', async (route) => {
      await fulfillJson(route, { status: 200, body: systemStatus });
    });

    await page.route('**/providers*', async (route) => {
      const method = route.request().method();
      const body = method === 'GET' ? {} : readPostData(route);
      captured.push({
        url: route.request().url(),
        method,
        body,
      });

      if (method === 'GET') {
        await fulfillJson(route, { status: 200, body: providerSettings });
        return;
      }

      if (method === 'PUT' || method === 'PATCH') {
        if (typeof body.default_provider === 'string') {
          accountPreferences.default_provider = body.default_provider;
        }
        if (typeof body.default_model === 'string') {
          accountPreferences.default_model = body.default_model;
        }
        if (typeof body.value === 'string' && route.request().url().includes('/settings/')) {
          const key = route.request().url().split('/settings/').pop() || '';
          accountPreferences[key] = body.value;
        }
        await fulfillJson(route, { status: 200, body: { success: true } });
        return;
      }

      await fulfillJson(route, { status: 405, body: { error: 'Method not allowed' } });
    });

    await page.route('**/account/preferences', async (route) => {
      const method = route.request().method();
      const body = method === 'GET' ? {} : readPostData(route);
      captured.push({
        url: route.request().url(),
        method,
        body,
      });

      if (method === 'GET') {
        await fulfillJson(route, { status: 200, body: accountPreferences });
        return;
      }

      if (method === 'PUT' || method === 'PATCH') {
        if (typeof body.default_provider === 'string') {
          accountPreferences.default_provider = body.default_provider;
        }
        if (typeof body.default_model === 'string') {
          accountPreferences.default_model = body.default_model;
        }
        await fulfillJson(route, { status: 200, body: { success: true } });
        return;
      }

      await fulfillJson(route, { status: 405, body: { error: 'Method not allowed' } });
    });

    await page.route('**/chat/estimate-tokens**', async (route) => {
      const body = readPostData(route);
      captured.push({
        url: route.request().url(),
        method: route.request().method(),
        body,
      });
      await fulfillJson(route, {
        status: 200,
        body: {
          input_tokens: 8,
          estimated_output_tokens: 32,
          estimated_cost_usd: 0.0004,
          provider: String(body.provider || 'openai'),
          model: String(body.model || 'gpt-4o-mini'),
          layers: [{ name: 'message', tokens: 8 }],
          degraded_mode: false,
        },
      });
    });

    await page.route('**/chat/conversations', async (route) => {
      const method = route.request().method();
      const body = method === 'GET' ? {} : readPostData(route);
      captured.push({
        url: route.request().url(),
        method,
        body,
      });

      if (method === 'GET') {
        await fulfillJson(route, {
          status: 200,
          body: Array.from(conversations.values()).map(summarizeConversation),
        });
        return;
      }

      if (method === 'POST') {
        const requestIndex = nextConversationIndex++;
        const outcome = await createConversationResponder({
          requestBody: body,
          requestIndex,
        });
        if (outcome.status >= 200 && outcome.status < 300) {
          const conversationId = String(
            typeof outcome.body === 'object' && outcome.body !== null && 'conversation_id' in outcome.body
              ? (outcome.body as Record<string, unknown>).conversation_id
              : `conv-brutal-${String(requestIndex).padStart(3, '0')}`
          );
          conversations.set(conversationId, {
            conversation_id: conversationId,
            title: String(
              typeof body.title === 'string'
                ? body.title
                : (outcome.body as Record<string, unknown>)?.title || 'New critical journey chat'
            ),
            created_at: NOW_ISO,
            updated_at: NOW_ISO,
            messages: [],
          });
        }
        await fulfillJson(route, outcome);
        return;
      }

      await fulfillJson(route, { status: 405, body: { error: 'Method not allowed' } });
    });

    await page.route(/\/chat\/conversations\/([^/]+)$/, async (route) => {
      const conversationId = route.request().url().split('/chat/conversations/')[1].split('?')[0];
      const body = route.request().method() === 'GET' ? {} : readPostData(route);
      captured.push({
        url: route.request().url(),
        method: route.request().method(),
        body,
      });

      const record = conversations.get(conversationId);
      if (!record) {
        await fulfillJson(route, {
          status: 404,
          body: { error: 'Conversation not found' },
        });
        return;
      }

      if (route.request().method() === 'GET') {
        await fulfillJson(route, { status: 200, body: buildDetail(record) });
        return;
      }

      await fulfillJson(route, { status: 405, body: { error: 'Method not allowed' } });
    });

    await page.route(/\/chat\/conversations\/([^/]+)\/messages$/, async (route) => {
      const conversationId = route.request().url().split('/chat/conversations/')[1].split('/messages')[0];
      const body = readPostData(route);
      captured.push({
        url: route.request().url(),
        method: route.request().method(),
        body,
      });

      if (route.request().method() !== 'POST') {
        await fulfillJson(route, { status: 405, body: { error: 'Method not allowed' } });
        return;
      }

      const existing = conversations.get(conversationId) || {
        conversation_id: conversationId,
        title: String(body.message || body.prompt || 'New critical journey chat').slice(0, 48),
        created_at: NOW_ISO,
        updated_at: NOW_ISO,
        messages: [],
      };

      const requestIndex = ++nextMessageIndex;
      const outcome = await sendMessageResponder({
        requestBody: body,
        requestIndex,
        conversationId,
        conversation: existing,
      });

      if (outcome.status >= 200 && outcome.status < 300) {
        conversations.set(conversationId, existing);
      }

      await fulfillJson(route, outcome);
    });

    await page.route('**/chat/upload-file', async (route) => {
      const body = route.request().method() === 'POST' ? { formData: true } : {};
      captured.push({
        url: route.request().url(),
        method: route.request().method(),
        body,
      });
      await fulfillJson(route, {
        status: 200,
        body: {
          file_id: 'file-tool-context',
          filename: 'tool-context.txt',
          mime_type: 'text/plain',
          size_bytes: 22,
        },
      });
    });

    await page.route('**/sandbox/jobs', async (route) => {
      const method = route.request().method();
      const body = method === 'GET' ? {} : readPostData(route);
      captured.push({
        url: route.request().url(),
        method,
        body,
      });
      if (sandboxJobsResponse instanceof Error) {
        await fulfillJson(route, { status: 503, body: { success: false, error: sandboxJobsResponse.message } });
        return;
      }
      if (
        typeof sandboxJobsResponse === 'object' &&
        sandboxJobsResponse !== null &&
        'error' in sandboxJobsResponse &&
        !('status' in sandboxJobsResponse)
      ) {
        await fulfillJson(route, {
          status: 503,
          body: sandboxJobsResponse,
        });
        return;
      }
      if (typeof sandboxJobsResponse === 'object' && sandboxJobsResponse && 'status' in sandboxJobsResponse) {
        await fulfillJson(route, sandboxJobsResponse as RouteOutcome);
        return;
      }
      await fulfillJson(route, { status: 200, body: sandboxJobsResponse });
    });

    await page.route('**/sandbox/run', async (route) => {
      const body = readPostData(route);
      captured.push({
        url: route.request().url(),
        method: route.request().method(),
        body,
      });
      await fulfillJson(route, sandboxRunResponse);
    });

    await page.route('**/health*', async (route) => {
      await fulfillJson(route, { status: 200, body: healthResponse });
    });
  };

  return {
    captured,
    conversations,
    install,
    state: {
      setAuthValidateResponse(next: RouteOutcome) {
        authValidateResponse = next;
      },
      setRegisterResponse(next: RouteOutcome) {
        registerResponse = next;
      },
      setLoginResponse(next: RouteOutcome) {
        loginResponse = next;
      },
      setModelsResponse(next: unknown) {
        modelsResponse = next;
      },
      setSystemStatus(next: typeof systemStatus) {
        systemStatus = next;
      },
      setHealthResponse(next: typeof healthResponse) {
        healthResponse = next;
      },
      setProviderSettings(next: typeof providerSettings) {
        providerSettings = next;
      },
      setAccountPreferences(next: typeof accountPreferences) {
        accountPreferences = next;
      },
      setSandboxJobsResponse(next: unknown) {
        sandboxJobsResponse = next;
      },
      setSandboxRunResponse(next: RouteOutcome) {
        sandboxRunResponse = next;
      },
      setCreateConversationResponder(
        next: (ctx: CreateResponderContext) => Promise<RouteOutcome> | RouteOutcome
      ) {
        createConversationResponder = next;
      },
      setSendMessageResponder(
        next: (ctx: SendResponderContext) => Promise<RouteOutcome> | RouteOutcome
      ) {
        sendMessageResponder = next;
      },
      seedConversation(record: ConversationRecord) {
        conversations.set(record.conversation_id, record);
      },
      clearConversations() {
        conversations.clear();
      },
      addConversation(
        conversationId: string,
        title: string,
        messages: ConversationMessage[] = []
      ) {
        conversations.set(conversationId, {
          conversation_id: conversationId,
          title,
          created_at: NOW_ISO,
          updated_at: NOW_ISO,
          messages,
        });
      },
      pushMessage(conversationId: string, role: 'user' | 'assistant', content: string, metadata?: Record<string, unknown>) {
        const record =
          conversations.get(conversationId) ||
          ({
            conversation_id: conversationId,
            title: content.slice(0, 48) || 'New critical journey chat',
            created_at: NOW_ISO,
            updated_at: NOW_ISO,
            messages: [],
          } as ConversationRecord);
        record.messages.push(createConversationMessage(role, content, nextMessageIndex++, metadata));
        record.updated_at = NOW_ISO;
        conversations.set(conversationId, record);
      },
      get requestCounts() {
        return {
          total: captured.length,
          messages: captured.filter((request) => /\/messages$/.test(request.url)).length,
          conversations: captured.filter((request) => /\/conversations(?:\?.*)?$/.test(request.url)).length,
        };
      },
    },
    defaults: {
      nowIso: NOW_ISO,
      defaultChatUsage,
    },
  };
}
