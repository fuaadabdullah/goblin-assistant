import '@testing-library/jest-dom';

// Mock dependencies before importing api
jest.mock('axios', () => {
  const mockAxiosInstance = {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    patch: jest.fn(),
    interceptors: {
      response: { use: jest.fn() },
    },
  };
  return {
    __esModule: true,
    default: {
      create: jest.fn(() => mockAxiosInstance),
      isAxiosError: jest.fn(() => false),
    },
    AxiosError: class extends Error {},
  };
});

jest.mock('../../config/env', () => ({
  env: { apiBaseUrl: 'http://localhost:8000' },
}));

jest.mock('../../utils/dev-log', () => ({
  devWarn: jest.fn(),
  devError: jest.fn(),
  devLog: jest.fn(),
}));

const mockGetAuthToken = jest.fn().mockReturnValue('test-token');
const mockGetRefreshToken = jest.fn().mockReturnValue('refresh-token');
const mockPersistAuthSession = jest.fn();
const mockClearAuthSession = jest.fn();

jest.mock('../../utils/auth-session', () => ({
  getAuthToken: () => mockGetAuthToken(),
  getRefreshToken: () => mockGetRefreshToken(),
  persistAuthSession: (...args: unknown[]) => mockPersistAuthSession(...args),
  clearAuthSession: () => mockClearAuthSession(),
}));

import axios from 'axios';
import { apiClient } from '../api';

// Save mock instance references immediately after import (before any test clears them)
// axios.create returns the same mockAxiosInstance for every call, so both backend & frontend share it
const mockHttp = (axios.create as jest.Mock).mock.results[0]?.value;

describe('apiClient', () => {
  beforeEach(() => {
    // Clear call tracking on http methods, but not the reference itself
    mockHttp.get.mockClear();
    mockHttp.post.mockClear();
    mockHttp.put.mockClear();
    mockHttp.patch.mockClear();
    mockGetAuthToken.mockClear();
    mockGetRefreshToken.mockClear();
    mockPersistAuthSession.mockClear();
    mockClearAuthSession.mockClear();
  });

  describe('generate', () => {
    it('calls frontend post with prompt', async () => {
      
      mockHttp.post.mockResolvedValueOnce({ data: { content: 'hello' } });
      const result = await apiClient.generate('test prompt');
      expect(mockHttp.post).toHaveBeenCalledWith('/api/generate', { prompt: 'test prompt', model: undefined }, undefined);
      expect(result).toEqual({ content: 'hello' });
    });
  });

  describe('getAllHealth', () => {
    it('returns health status', async () => {
      
      const healthData = { overall: 'healthy', timestamp: '2024-01-01', services: {} };
      mockHttp.get.mockResolvedValueOnce({ data: healthData });
      const result = await apiClient.getAllHealth();
      expect(result).toEqual(healthData);
    });

    it('returns unhealthy on error', async () => {
      
      mockHttp.get.mockRejectedValueOnce(new Error('fail'));
      const result = await apiClient.getAllHealth();
      expect(result.overall).toBe('unhealthy');
    });
  });

  describe('getStreamingHealth', () => {
    it('returns streaming health', async () => {
      
      mockHttp.get.mockResolvedValueOnce({ data: { status: 'ok' } });
      const result = await apiClient.getStreamingHealth();
      expect(result).toEqual({ status: 'ok' });
    });

    it('returns unknown on error', async () => {
      
      mockHttp.get.mockRejectedValueOnce(new Error('fail'));
      const result = await apiClient.getStreamingHealth();
      expect(result).toEqual({ status: 'unknown' });
    });
  });

  describe('getRoutingHealth', () => {
    it('returns routing health', async () => {
      
      mockHttp.get.mockResolvedValueOnce({ data: { status: 'ok' } });
      const result = await apiClient.getRoutingHealth();
      expect(result).toEqual({ status: 'ok' });
    });

    it('returns unknown on error', async () => {
      
      mockHttp.get.mockRejectedValueOnce(new Error('fail'));
      const result = await apiClient.getRoutingHealth();
      expect(result).toEqual({ status: 'unknown' });
    });
  });

  describe('getProviderSettings', () => {
    it('calls backend GET /providers', async () => {
      
      mockHttp.get.mockResolvedValueOnce({ data: [{ id: 1, name: 'openai' }] });
      const result = await apiClient.getProviderSettings();
      expect(result).toEqual([{ id: 1, name: 'openai' }]);
    });
  });

  describe('getModelConfigs', () => {
    it('calls frontend GET /api/models', async () => {
      
      mockHttp.get.mockResolvedValueOnce({ data: [{ model: 'gpt-4' }] });
      const result = await apiClient.getModelConfigs();
      expect(result).toEqual([{ model: 'gpt-4' }]);
    });
  });

  describe('updateProvider', () => {
    it('calls backend PATCH', async () => {
      
      mockHttp.patch.mockResolvedValueOnce({ data: { ok: true } });
      await apiClient.updateProvider(1, { enabled: true });
      expect(mockHttp.patch).toHaveBeenCalledWith('/providers/1', { enabled: true }, undefined);
    });
  });

  describe('setProviderPriority', () => {
    it('calls backend POST', async () => {
      
      mockHttp.post.mockResolvedValueOnce({ data: { ok: true } });
      await apiClient.setProviderPriority(1, 5, 'default');
      expect(mockHttp.post).toHaveBeenCalledWith(
        '/providers/1/priority',
        { priority: 5, role: 'default' },
        undefined,
      );
    });
  });

  describe('testProviderConnection', () => {
    it('calls backend POST', async () => {
      
      mockHttp.post.mockResolvedValueOnce({ data: { connected: true } });
      await apiClient.testProviderConnection(1);
      expect(mockHttp.post).toHaveBeenCalledWith('/providers/1/test', undefined, undefined);
    });
  });

  describe('getRaptorLogs', () => {
    it('calls backend GET with limit', async () => {
      
      mockHttp.get.mockResolvedValueOnce({ data: [] });
      await apiClient.getRaptorLogs(50);
      expect(mockHttp.get).toHaveBeenCalledWith('/logs?limit=50', undefined);
    });
  });

  describe('login', () => {
    it('gets csrf token then posts login', async () => {
      
      // First call: csrf-token
      mockHttp.get.mockResolvedValueOnce({ data: { csrf_token: 'csrf123' } });
      // Second call: login
      mockHttp.post.mockResolvedValueOnce({ data: { access_token: 'tok' } });
      const result = await apiClient.login('test@example.com', 'password');
      expect(result).toEqual({ access_token: 'tok' });
    });
  });

  describe('register', () => {
    it('gets csrf token then posts register', async () => {
      
      mockHttp.get.mockResolvedValueOnce({ data: { csrf_token: 'csrf123' } });
      mockHttp.post.mockResolvedValueOnce({ data: { access_token: 'tok' } });
      const result = await apiClient.register('test@example.com', 'password', 'turnstile-tok');
      expect(result).toEqual({ access_token: 'tok' });
    });
  });

  describe('createConversation', () => {
    it('creates and returns mapped conversation', async () => {
      
      mockHttp.post.mockResolvedValueOnce({
        data: {
          conversation_id: 'conv-1',
          title: 'Test Chat',
          created_at: '2024-01-01',
        },
      });
      const result = await apiClient.createConversation('Test Chat');
      expect(result).toEqual({
        conversationId: 'conv-1',
        title: 'Test Chat',
        createdAt: '2024-01-01',
      });
    });
  });

  describe('listConversations', () => {
    it('returns mapped conversations', async () => {
      
      mockHttp.get.mockResolvedValueOnce({
        data: [{
          conversation_id: 'conv-1',
          title: 'Test',
          snippet: 'hello',
          created_at: '2024-01-01',
          updated_at: '2024-01-02',
          message_count: 5,
        }],
      });
      const result = await apiClient.listConversations();
      expect(result[0].conversationId).toBe('conv-1');
      expect(result[0].messageCount).toBe(5);
    });
  });

  describe('getConversation', () => {
    it('returns mapped conversation with messages', async () => {
      
      mockHttp.get.mockResolvedValueOnce({
        data: {
          conversation_id: 'conv-1',
          title: 'Test',
          created_at: '2024-01-01',
          updated_at: '2024-01-02',
          messages: [
            { message_id: 'msg-1', role: 'user', content: 'hi', timestamp: '2024-01-01', metadata: { foo: 'bar' } },
          ],
        },
      });
      const result = await apiClient.getConversation('conv-1');
      expect(result.messages[0].id).toBe('msg-1');
      expect(result.messages[0].meta).toEqual({ foo: 'bar' });
    });
  });

  describe('sendConversationMessage', () => {
    it('sends and returns mapped response', async () => {
      
      mockHttp.post.mockResolvedValueOnce({
        data: {
          message_id: 'msg-1',
          response: 'Hello!',
          provider: 'openai',
          model: 'gpt-4',
          timestamp: '2024-01-01',
          usage: { total_tokens: 100 },
          cost_usd: 0.01,
          correlation_id: 'corr-1',
        },
      });
      const result = await apiClient.sendConversationMessage({
        conversationId: 'conv-1',
        message: 'Hi',
        model: 'gpt-4',
      });
      expect(result.messageId).toBe('msg-1');
      expect(result.content).toBe('Hello!');
      expect(result.cost_usd).toBe(0.01);
    });
  });

  describe('chatCompletion', () => {
    it('returns content string', async () => {
      
      mockHttp.post.mockResolvedValueOnce({ data: { content: 'response text' } });
      const result = await apiClient.chatCompletion([{ role: 'user', content: 'hi' }]);
      expect(result).toBe('response text');
    });

    it('returns choice message content if no direct content', async () => {
      
      mockHttp.post.mockResolvedValueOnce({
        data: { choices: [{ message: { content: 'from choice' } }] },
      });
      const result = await apiClient.chatCompletion([{ role: 'user', content: 'hi' }]);
      expect(result).toBe('from choice');
    });
  });

  describe('getGoogleAuthUrl', () => {
    it('returns url from response', async () => {
      
      mockHttp.get.mockResolvedValueOnce({ data: { url: 'https://google.com/auth' } });
      const result = await apiClient.getGoogleAuthUrl();
      expect(result.url).toBe('https://google.com/auth');
    });

    it('throws if no url in response', async () => {
      
      mockHttp.get.mockResolvedValueOnce({ data: {} });
      await expect(apiClient.getGoogleAuthUrl()).rejects.toThrow('Google sign-in URL is unavailable.');
    });
  });

  describe('validateToken', () => {
    it('posts to /api/auth/validate', async () => {
      
      mockHttp.post.mockResolvedValueOnce({ data: { valid: true } });
      const result = await apiClient.validateToken('tok123');
      expect(result).toEqual({ valid: true });
    });
  });

  describe('searchQuery', () => {
    it('calls backend POST /search/query', async () => {
      
      mockHttp.post.mockResolvedValueOnce({ data: [{ id: '1' }] });
      await apiClient.searchQuery('docs', 'test');
      expect(mockHttp.post).toHaveBeenCalledWith('/search/query', { collection: 'docs', query: 'test', limit: 8 }, undefined);
    });
  });

  describe('runSandboxCode', () => {
    it('calls backend POST /sandbox/run', async () => {
      
      mockHttp.post.mockResolvedValueOnce({ data: { output: 'hello' } });
      await apiClient.runSandboxCode({ code: 'print("hello")', language: 'python' });
      expect(mockHttp.post).toHaveBeenCalledWith('/sandbox/run', { code: 'print("hello")', language: 'python' }, undefined);
    });
  });

  describe('saveAccountProfile', () => {
    it('calls backend PUT /account/profile', async () => {
      
      mockHttp.put.mockResolvedValueOnce({ data: { ok: true } });
      await apiClient.saveAccountProfile({ name: 'Test' });
      expect(mockHttp.put).toHaveBeenCalledWith('/account/profile', { name: 'Test' }, undefined);
    });
  });

  describe('saveAccountPreferences', () => {
    it('calls backend PUT /account/preferences', async () => {
      
      mockHttp.put.mockResolvedValueOnce({ data: { ok: true } });
      await apiClient.saveAccountPreferences({ theme: 'dark' });
      expect(mockHttp.put).toHaveBeenCalledWith('/account/preferences', { theme: 'dark' }, undefined);
    });
  });

  describe('uploadFile', () => {
    it('posts FormData to /chat/upload-file', async () => {
      
      mockHttp.post.mockResolvedValueOnce({
        data: { file_id: 'f1', filename: 'test.txt', mime_type: 'text/plain', size_bytes: 100 },
      });
      const file = new File(['hello'], 'test.txt', { type: 'text/plain' });
      const result = await apiClient.uploadFile(file);
      expect(result.file_id).toBe('f1');
      expect(mockHttp.post).toHaveBeenCalledWith('/chat/upload-file', expect.any(FormData), expect.anything());
    });
  });

  describe('importConversationMessages', () => {
    it('posts to /chat/conversations/:id/import', async () => {
      
      mockHttp.post.mockResolvedValueOnce({ data: { success: true, imported_count: 2 } });
      const messages = [
        { id: 'm1', role: 'user' as const, content: 'hi', createdAt: '2024-01-01' },
      ];
      const result = await apiClient.importConversationMessages('conv-1', messages);
      expect(result).toEqual({ success: true, imported_count: 2 });
    });
  });

  describe('passkey methods', () => {
    it('passkeyChallenge calls POST', async () => {
      
      mockHttp.post.mockResolvedValueOnce({ data: { challenge: 'abc' } });
      await apiClient.passkeyChallenge('test@example.com');
      expect(mockHttp.post).toHaveBeenCalledWith('/auth/passkey/challenge', { email: 'test@example.com' }, undefined);
    });
  });

  describe('logout', () => {
    it('calls POST /auth/logout', async () => {
      
      mockHttp.post.mockResolvedValueOnce({ data: { ok: true } });
      await apiClient.logout();
      expect(mockHttp.post).toHaveBeenCalledWith('/auth/logout', undefined, expect.anything());
    });
  });

  describe('reorderProviders', () => {
    it('calls POST /providers/reorder', async () => {
      
      mockHttp.post.mockResolvedValueOnce({ data: { ok: true } });
      await apiClient.reorderProviders([1, 2, 3]);
      expect(mockHttp.post).toHaveBeenCalledWith('/providers/reorder', { providerIds: [1, 2, 3] }, undefined);
    });
  });

  describe('getGlobalSettings', () => {
    it('calls GET /settings', async () => {
      
      mockHttp.get.mockResolvedValueOnce({ data: { setting: 'value' } });
      const result = await apiClient.getGlobalSettings();
      expect(result).toEqual({ setting: 'value' });
    });
  });

  describe('updateGlobalSetting', () => {
    it('calls PATCH /settings/:key', async () => {
      
      mockHttp.patch.mockResolvedValueOnce({ data: { ok: true } });
      await apiClient.updateGlobalSetting('theme', 'dark');
      expect(mockHttp.patch).toHaveBeenCalledWith('/settings/theme', { value: 'dark' }, undefined);
    });
  });
});
