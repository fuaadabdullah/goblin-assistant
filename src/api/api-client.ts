export interface RuntimeClient {
  getGoblins(): Promise<GoblinStatus[]>;
  getProviders(): Promise<string[]>;
  getProviderModels(provider: string): Promise<string[]>;
  executeTask(
    goblin: string,
    task: string,
    streaming?: boolean,
    code?: string,
    provider?: string,
    model?: string
  ): Promise<string>;
  executeTaskStreaming(
    goblin: string,
    task: string,
    onChunk: (chunk: StreamChunk) => void,
    onComplete?: (response: TaskResponse) => void,
    code?: string,
    provider?: string,
    model?: string
  ): Promise<void>;
  setProviderApiKey(provider: string, key: string): Promise<void>;
  storeApiKey(provider: string, key: string): Promise<void>;
  getApiKey(provider: string): Promise<string | null>;
  clearApiKey(provider: string): Promise<void>;
  getHistory(goblin: string, limit?: number): Promise<MemoryEntry[]>;
  getStats(goblin: string): Promise<GoblinStats>;
  getCostSummary(): Promise<CostSummary>;
  parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan>;
  onTaskStream(callback: (payload: StreamChunk) => void): Promise<void>;
  // Authentication methods
  login(email: string, password: string): Promise<{ token: string; user: User }>;
  register(email: string, password: string, name?: string): Promise<{ token: string; user: User }>;
  logout(): Promise<void>;
  validateToken(token: string): Promise<{ valid: boolean; user?: User }>;
}

import { api } from './http-client';
import { trackApiCall, trackLLMOperation, APIError, NetworkError } from '../utils/error-tracking';

// FastAPI backend URL (when using the FastAPI runtime)
const FASTAPI_BASE = import.meta.env.VITE_FASTAPI_URL || 'http://127.0.0.1:8000';
const RUNTIME: string = (import.meta.env.VITE_GOBLIN_RUNTIME as string) || 'fastapi';
const MOCK_API: boolean = import.meta.env.VITE_MOCK_API === 'true';

// Runtime selection: 'fastapi' for development (Vite + FastAPI), 'demo' for demonstrations
// Set VITE_GOBLIN_RUNTIME in .env file or environment variables
// Mock API: returns static data for testing when backend is unavailable
// Set VITE_MOCK_API=true in .env file or environment variables

export interface GoblinStatus {
  id: string;
  name: string;
  title: string;
  status: string;
  guild?: string;
}

export interface ProviderSettings {
  name: string;
  api_key?: string;
  base_url?: string;
  models: string[];
  enabled: boolean;
}

export interface ModelSettings {
  name: string;
  provider: string;
  model_id: string;
  temperature?: number;
  max_tokens?: number;
  enabled: boolean;
}

export interface SettingsResponse {
  providers: ProviderSettings[];
  models: ModelSettings[];
  default_provider?: string;
  default_model?: string;
}

export interface GoblinResponse {
  goblin: string;
  task: string;
  reasoning: string;
  tool?: string;
  command?: string;
  output?: string;
  duration_ms: number;
  cost?: number;
  model?: string;
  provider?: string;
}

export interface User {
  id: string;
  email: string;
  name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  token: string;
  user: User;
}

export interface TokenValidationResponse {
  valid: boolean;
  user?: User;
}

export interface MemoryEntry {
  id: string;
  goblin: string;
  task: string;
  response: string;
  timestamp: number;
  kpis?: string;
}

export interface CostSummary {
  total_cost: number;
  cost_by_provider: Record<string, number>;
  cost_by_model: Record<string, number>;
}

export interface OrchestrationStep {
  id: string;
  goblin: string;
  task: string;
  dependencies: string[];
  batch: number;
}

export interface OrchestrationPlan {
  steps: OrchestrationStep[];
  total_batches: number;
  max_parallel: number;
  estimated_cost?: number;
}

export interface StreamEvent {
  content: string;
  done: boolean;
}

export interface GoblinStats {
  total_tasks?: number;
  total_cost?: number;
  avg_duration_ms?: number;
  success_rate?: number;
  [key: string]: unknown; // Allow additional dynamic properties
}

export interface StreamChunk {
  content?: string;
  result?: unknown;
  done?: boolean;
  [key: string]: unknown; // Allow additional dynamic properties
}

export interface TaskResponse {
  taskId?: string;
  result?: unknown;
  [key: string]: unknown; // Allow additional dynamic properties
}

export interface DemoStepData {
  response: string;
  cost: number;
  tokens: number;
}

// FastAPI-based runtime client (direct HTTP + SSE streaming)
export class FastApiRuntimeClient implements RuntimeClient {
  async getGoblins(): Promise<GoblinStatus[]> {
    return [];
  }
  async getProviders(): Promise<string[]> {
    return trackApiCall(
      async () => {
        const response = await api.get<string[]>('/routing/providers');
        return response.data || [];
      },
      '/routing/providers',
      'GET'
    );
  }
  async getProviderModels(provider: string): Promise<string[]> {
    return trackApiCall(
      async () => {
        const response = await api.get<string[]>(`/routing/providers/${provider}`);
        return response.data || [];
      },
      `/routing/providers/${provider}`,
      'GET',
      { provider }
    );
  }
  async executeTask(
    goblin: string,
    task: string,
    _streaming = false,
    code?: string,
    provider?: string,
    model?: string
  ): Promise<string> {
    const response = await api.post<{ taskId: string }>('/execute', {
      goblin,
      task,
      code,
      provider,
      model,
    });
    return response.data.taskId;
  }

  async storeApiKey(provider: string, key: string): Promise<void> {
    await api.post(`/api-keys/${provider}`, key);
  }

  async getApiKey(provider: string): Promise<string | null> {
    try {
      const response = await api.get<{ key?: string }>(`/api-keys/${provider}`);
      return response.data.key || null;
    } catch (error) {
      // Return null if key doesn't exist
      return null;
    }
  }

  async clearApiKey(provider: string): Promise<void> {
    await api.delete(`/api-keys/${provider}`);
  }
  async getHistory(_goblin: string, _limit = 10): Promise<MemoryEntry[]> {
    return [];
  }
  async getStats(_goblin: string): Promise<GoblinStats> {
    return {};
  }
  async getCostSummary(): Promise<CostSummary> {
    return { total_cost: 0, cost_by_provider: {}, cost_by_model: {} };
  }
  async parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan> {
    const response = await api.post<OrchestrationPlan>('/parse', {
      text,
      default_goblin: defaultGoblin,
    });
    return response.data;
  }

  async executeTaskStreaming(
    goblin: string,
    task: string,
    onChunk: (chunk: StreamChunk) => void,
    onComplete?: (response: TaskResponse) => void,
    code?: string,
    provider?: string,
    model?: string
  ): Promise<void> {
    return trackLLMOperation(
      async () => {
        const taskId = await this.executeTask(goblin, task, true, code, provider, model);
        // open a streaming connection to /stream endpoint
        const evtSourceUrl = `${FASTAPI_BASE}/stream?task_id=${taskId}&goblin=${encodeURIComponent(goblin)}&task=${encodeURIComponent(task)}`;
        const evtSource = new EventSource(evtSourceUrl);
        return new Promise<void>((resolve, reject) => {
          evtSource.onmessage = (e: MessageEvent) => {
            try {
              const payload = JSON.parse(e.data);
              onChunk(payload);
              if (payload.result !== undefined) {
                if (onComplete) onComplete(payload);
                evtSource.close();
                resolve();
              }
            } catch (err) {
              // ignore parse errors
            }
          };
          evtSource.onerror = err => {
            try {
              evtSource.close();
            } catch (e) {
              /* ignore cleanup errors */
            }
            reject(err);
          };
        });
      },
      {
        provider: provider || 'unknown',
        model: model || 'unknown',
        operation: `executeTaskStreaming: ${goblin} - ${task}`,
      }
    );
  }

  async onTaskStream(_callback: (payload: StreamChunk) => void) {
    /* no-op */
  }
  async setProviderApiKey(_provider: string, _key: string): Promise<void> {
    return;
  }

  // Authentication methods
  async login(email: string, password: string): Promise<{ token: string; user: User }> {
    return trackApiCall(
      async () => {
        const response = await api.post<{ token: string; user: User }>('/auth/login', {
          email,
          password,
        });
        return response.data;
      },
      '/auth/login',
      'POST',
      { email: email.replace(/./g, '*') } // Mask email for privacy
    );
  }

  async register(email: string, password: string, name?: string): Promise<{ token: string; user: User }> {
    return trackApiCall(
      async () => {
        const response = await api.post<{ token: string; user: User }>('/auth/register', {
          email,
          password,
          name,
        });
        return response.data;
      },
      '/auth/register',
      'POST',
      { email: email.replace(/./g, '*'), name } // Mask email for privacy
    );
  }

  async logout(): Promise<void> {
    return trackApiCall(
      async () => {
        await api.post('/auth/logout');
      },
      '/auth/logout',
      'POST'
    );
  }

  async validateToken(token: string): Promise<{ valid: boolean; user?: User }> {
    return trackApiCall(
      async () => {
        const response = await api.post<{ valid: boolean; user?: User }>(
          '/auth/validate',
          {},
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        return response.data;
      },
      '/auth/validate',
      'POST'
    );
  }
}

// Demo runtime client for interview demonstrations - provides deterministic, pre-recorded responses
export class DemoRuntimeClient implements RuntimeClient {
  // Pre-recorded responses for common orchestration templates
  private readonly demoResponses = {
    'docs-writer: document this code THEN code-writer: write a unit test': {
      'docs-writer': {
        response: `# add(a, b) Function Documentation

## Overview
A simple arithmetic function that adds two numbers together.

## Parameters
- \`a\` (number): The first number to add
- \`b\` (number): The second number to add

## Returns
- \`number\`: The sum of a and b

## Example Usage
\`\`\`javascript
const result = add(5, 3); // Returns 8
\`\`\`

## Notes
This function performs basic addition without any error checking or type validation.`,
        cost: 0.012,
        tokens: 156,
      },
      'code-writer': {
        response: `# Unit Test for add() Function

\`\`\`javascript
describe('add() function', () => {
  test('adds two positive numbers correctly', () => {
    expect(add(2, 3)).toBe(5);
    expect(add(10, 15)).toBe(25);
  });

  test('adds positive and negative numbers correctly', () => {
    expect(add(5, -3)).toBe(2);
    expect(add(-2, -3)).toBe(-5);
  });

  test('adds with zero correctly', () => {
    expect(add(0, 5)).toBe(5);
    expect(add(5, 0)).toBe(5);
    expect(add(0, 0)).toBe(0);
  });

  test('handles decimal numbers', () => {
    expect(add(1.5, 2.5)).toBe(4);
    expect(add(0.1, 0.2)).toBeCloseTo(0.3);
  });
});
\`\`\``,
        cost: 0.018,
        tokens: 203,
      },
    },
    'code-writer: analyze this code for issues THEN code-writer: suggest optimizations': {
      'code-writer': {
        response: `# Code Analysis: add() Function

## Issues Found
1. **No input validation**: Function doesn't check if inputs are numbers
2. **No error handling**: Will return NaN for invalid inputs like strings
3. **Limited type safety**: No TypeScript types or JSDoc annotations
4. **No edge case handling**: Doesn't handle very large numbers or special values

## Potential Runtime Issues
- \`add("5", "3")\` returns "53" (string concatenation)
- \`add(null, 5)\` returns 5 (type coercion)
- \`add(undefined, 5)\` returns NaN
- \`add(Infinity, -Infinity)\` returns NaN

## Recommendations
1. Add input type checking
2. Add JSDoc documentation
3. Consider using TypeScript for better type safety
4. Add error handling for edge cases`,
        cost: 0.015,
        tokens: 178,
      },
      'code-writer-2': {
        response: `# Optimization Suggestions for add() Function

## Performance Optimizations
1. **Use strict equality**: No changes needed for simple addition
2. **Avoid unnecessary operations**: Current implementation is already optimal

## Code Quality Improvements
\`\`\`javascript
/**
 * Adds two numbers together
 * @param {number} a - First number
 * @param {number} b - Second number
 * @returns {number} Sum of a and b
 * @throws {TypeError} If inputs are not numbers
 */
function add(a, b) {
  if (typeof a !== 'number' || typeof b !== 'number') {
    throw new TypeError('Both arguments must be numbers');
  }
  if (!isFinite(a) || !isFinite(b)) {
    throw new RangeError('Arguments must be finite numbers');
  }
  return a + b;
}
\`\`\`

## Benefits of Changes
- **Type Safety**: Prevents string concatenation and type coercion
- **Error Handling**: Clear error messages for invalid inputs
- **Documentation**: JSDoc provides better IDE support
- **Edge Case Handling**: Prevents NaN results from Infinity/-Infinity

## Alternative: TypeScript Version
\`\`\`typescript
function add(a: number, b: number): number {
  return a + b;
}
\`\`\``,
        cost: 0.022,
        tokens: 245,
      },
    },
  };

  async getGoblins(): Promise<GoblinStatus[]> {
    return [
      {
        id: 'docs-writer',
        name: 'docs-writer',
        title: 'Documentation Writer',
        status: 'available',
      },
      { id: 'code-writer', name: 'code-writer', title: 'Code Writer', status: 'available' },
    ];
  }

  async getProviders(): Promise<string[]> {
    return ['demo'];
  }

  async getProviderModels(_provider: string): Promise<string[]> {
    return ['demo-model'];
  }

  async executeTask(
    _goblin: string,
    _task: string,
    _streaming = false,
    _code?: string,
    _provider?: string,
    _model?: string
  ): Promise<string> {
    // Simulate async delay for realism
    await new Promise(resolve => setTimeout(resolve, 200));
    return `demo_task_${_goblin}_${Date.now()}`;
  }

  async getHistory(_goblin: string, _limit = 10): Promise<MemoryEntry[]> {
    return [];
  }

  async getStats(_goblin: string): Promise<GoblinStats> {
    return { total_tasks: 42, success_rate: 0.98 };
  }

  async getCostSummary(): Promise<CostSummary> {
    return {
      total_cost: 0.15,
      cost_by_provider: { demo: 0.15 },
      cost_by_model: { 'demo-model': 0.15 },
    };
  }

  async parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan> {
    // Parse the orchestration text to create steps
    const stepTexts = text.split('THEN').map(s => s.trim());
    const steps: OrchestrationStep[] = stepTexts.map((stepText, index) => {
      const [goblin, ...taskParts] = stepText.split(':');
      return {
        id: `step${index + 1}`,
        goblin: goblin?.trim() || defaultGoblin || 'docs-writer',
        task: taskParts.join(':').trim(),
        dependencies: index > 0 ? [`step${index}`] : [],
        batch: 0,
      };
    });
    return { steps, total_batches: 1, max_parallel: 1 };
  }

  async executeTaskStreaming(
    goblin: string,
    task: string,
    onChunk: (chunk: StreamChunk) => void,
    onComplete?: (response: TaskResponse) => void,
    _code?: string,
    _provider?: string,
    _model?: string
  ): Promise<void> {
    // Find the appropriate demo response based on the full orchestration
    const fullOrchestration = this.findOrchestrationFromTask(goblin, task);
    const demoData = fullOrchestration
      ? this.demoResponses[fullOrchestration as keyof typeof this.demoResponses]
      : null;

    let response: string;
    let cost: number;
    let tokens: number;

    if (demoData && demoData[goblin as keyof typeof demoData]) {
      const stepData = demoData[goblin as keyof typeof demoData] as DemoStepData;
      response = stepData.response;
      cost = stepData.cost;
      tokens = stepData.tokens;
    } else {
      // Fallback response for unrecognized tasks
      response = `Demo response: ${goblin} completed task "${task}" successfully. This is a pre-recorded demonstration response.`;
      cost = 0.01;
      tokens = 25;
    }

    // Simulate streaming by sending chunks
    const words = response.split(' ');
    let totalTokens = 0;
    let totalCost = 0;

    for (let i = 0; i < words.length; i++) {
      // Simulate realistic typing delay
      await new Promise(resolve => setTimeout(resolve, 30 + Math.random() * 20));

      const chunk = words[i] + (i < words.length - 1 ? ' ' : '');
      const chunkTokens = Math.ceil(chunk.length / 4); // Rough token estimation
      const chunkCost = (chunkTokens / tokens) * cost;

      totalTokens += chunkTokens;
      totalCost += chunkCost;

      onChunk({
        chunk,
        token_count: chunkTokens,
        cost_delta: chunkCost,
        taskId: `demo_${Date.now()}`,
        provider: 'demo',
        model: 'demo-model',
      });
    }

    // Send completion
    if (onComplete) {
      onComplete({
        result: response,
        cost: totalCost,
        tokens: totalTokens,
        model: 'demo-model',
        provider: 'demo',
        duration_ms: words.length * 50,
      });
    }
  }

  private findOrchestrationFromTask(goblin: string, task: string): string | null {
    // Try to match the current task to a known orchestration
    for (const [_orchestration, _responses] of Object.entries(this.demoResponses)) {
      if (
        _orchestration.includes(`${goblin}: ${task}`) ||
        _orchestration.includes(`${goblin}:${task}`)
      ) {
        return _orchestration;
      }
    }
    return null;
  }

  async onTaskStream(_callback: (payload: StreamChunk) => void) {
    /* no-op */
  }
  async setProviderApiKey(_provider: string, _key: string): Promise<void> {
    return;
  }
  async storeApiKey(_provider: string, _key: string): Promise<void> {
    return;
  }
  async getApiKey(_provider: string): Promise<string | null> {
    return 'demo-key';
  }
  async clearApiKey(_provider: string): Promise<void> {
    return;
  }

  // Authentication methods - demo implementation
  async login(email: string, _password: string): Promise<{ token: string; user: User }> {
    // Demo login - accepts any email with @demo.com
    if (!email.includes('@demo.com')) {
      throw new Error('Demo login requires @demo.com email');
    }
    return {
      token: 'demo-token-' + Date.now(),
      user: {
        id: 'demo-user',
        email: email,
        name: 'Demo User',
      },
    };
  }

  async register(email: string, _password: string, name?: string): Promise<{ token: string; user: User }> {
    // Demo registration - accepts any email
    return {
      token: 'demo-token-' + Date.now(),
      user: {
        id: 'demo-user-' + Date.now(),
        email: email,
        name: name || 'Demo User',
      },
    };
  }

  async logout(): Promise<void> {
    // Demo logout - no-op
    return;
  }

  async validateToken(token: string): Promise<{ valid: boolean; user?: User }> {
    // Demo token validation - accepts any token starting with 'demo-token'
    if (token.startsWith('demo-token-')) {
      return {
        valid: true,
        user: {
          id: 'demo-user',
          email: 'demo@example.com',
          name: 'Demo User',
        },
      };
    }
    return { valid: false };
  }
}

// Mock runtime client for testing when backend is unavailable
export class MockRuntimeClient implements RuntimeClient {
  async getGoblins(): Promise<GoblinStatus[]> {
    return [
      {
        id: 'docs-writer',
        name: 'docs-writer',
        title: 'Documentation Writer',
        status: 'available',
      },
      { id: 'code-writer', name: 'code-writer', title: 'Code Writer', status: 'available' },
    ];
  }

  async getProviders(): Promise<string[]> {
    return trackApiCall(
      async () => {
        const response = await api.get<string[]>('/routing/providers');
        return response.data || [];
      },
      '/routing/providers',
      'GET'
    );
  }

  async getProviderModels(provider: string): Promise<string[]> {
    try {
      // Try to get models from the routing system first
      const models = await trackApiCall(
        async () => {
          const response = await api.get<string[]>(`/routing/providers/${provider}`);
          return response.data || [];
        },
        `/routing/providers/${provider}`,
        'GET',
        { provider }
      );
      if (models && models.length > 0) {
        return models;
      }
    } catch (error) {
      console.warn(`Failed to get models from routing system for ${provider}, using fallback`);
    }

    // Fallback to hardcoded models if routing system fails
    const fallbackModels: Record<string, string[]> = {
      openai: ['gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo'],
      anthropic: ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
      gemini: ['gemini-pro', 'gemini-pro-vision'],
      ollama: ['llama2', 'codellama', 'mistral'],
      groq: ['mixtral-8x7b', 'llama2-70b'],
      deepseek: ['deepseek-chat', 'deepseek-coder'],
      together: ['llama-2-70b', 'codellama-34b'],
      replicate: ['llama-2-70b', 'codellama-34b'],
      huggingface: ['microsoft/DialoGPT-medium'],
      cohere: ['command', 'base'],
      ai21: ['j2-ultra', 'j2-mid'],
    };
    return fallbackModels[provider] || [];
  }

  async executeTask(
    _goblin: string,
    _task: string,
    _streaming = false,
    _code?: string,
    _provider?: string,
    _model?: string
  ): Promise<string> {
    // Simulate async delay
    await new Promise(resolve => setTimeout(resolve, 100));
    return `Executed: ${_task} using ${_goblin}`;
  }

  async getHistory(_goblin: string, _limit = 10): Promise<MemoryEntry[]> {
    return [];
  }

  async getStats(_goblin: string): Promise<GoblinStats> {
    return { total_tasks: 0, success_rate: 0 };
  }

  async getCostSummary(): Promise<CostSummary> {
    return { total_cost: 0, cost_by_provider: {}, cost_by_model: {} };
  }

  async parseOrchestration(text: string, defaultGoblin?: string): Promise<OrchestrationPlan> {
    // Simple mock parser
    const steps = text.split('THEN').map((step, index) => ({
      id: `step${index + 1}`,
      goblin: defaultGoblin || 'docs-writer',
      task: step.trim(),
      dependencies: [],
      batch: 0,
    }));
    return { steps, total_batches: 1, max_parallel: 1 };
  }

  async executeTaskStreaming(
    goblin: string,
    task: string,
    onChunk: (chunk: StreamChunk) => void,
    onComplete?: (response: TaskResponse) => void,
    _code?: string,
    provider?: string,
    model?: string
  ): Promise<void> {
    // Simulate streaming response
    const mockResponse = `Mock response for ${goblin}: ${task}`;
    const words = mockResponse.split(' ');

    for (let i = 0; i < words.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 50));
      onChunk({
        chunk: words[i] + ' ',
        token_count: 1,
        cost_delta: 0.001,
      });
    }

    if (onComplete) {
      onComplete({
        result: mockResponse,
        cost: words.length * 0.001,
        model: model || 'mock-model',
        provider: provider || 'mock-provider',
      });
    }
  }

  async onTaskStream(_callback: (payload: StreamChunk) => void) {
    /* no-op */
  }
  async setProviderApiKey(_provider: string, _key: string): Promise<void> {
    return;
  }
  async storeApiKey(_provider: string, _key: string): Promise<void> {
    return;
  }
  async getApiKey(_provider: string): Promise<string | null> {
    return null;
  }
  async clearApiKey(_provider: string): Promise<void> {
    return;
  }

  // Authentication methods - mock implementation
  async login(email: string, _password: string): Promise<{ token: string; user: User }> {
    // Mock login - accepts any email
    return {
      token: 'mock-token-' + Date.now(),
      user: {
        id: 'mock-user',
        email: email,
        name: 'Mock User',
      },
    };
  }

  async register(email: string, _password: string, name?: string): Promise<{ token: string; user: User }> {
    // Mock registration - accepts any email
    return {
      token: 'mock-token-' + Date.now(),
      user: {
        id: 'mock-user-' + Date.now(),
        email: email,
        name: name || 'Mock User',
      },
    };
  }

  async logout(): Promise<void> {
    // Mock logout - no-op
    return;
  }

  async validateToken(token: string): Promise<{ valid: boolean; user?: User }> {
    // Mock token validation - accepts any token starting with 'mock-token'
    if (token.startsWith('mock-token-')) {
      return {
        valid: true,
        user: {
          id: 'mock-user',
          email: 'mock@example.com',
          name: 'Mock User',
        },
      };
    }
    return { valid: false };
  }
}

export const runtimeClientFast = new FastApiRuntimeClient();
export const runtimeClientMock = new MockRuntimeClient();
export const runtimeClientDemo = new DemoRuntimeClient();

// dynamic selection of runtime client (keep runtimeClient name for compatibility)
export const runtimeClient = MOCK_API
  ? runtimeClientMock
  : RUNTIME === 'demo'
    ? runtimeClientDemo
    : runtimeClientFast;

// export chosen runtime client
export const runtime = runtimeClient;

// Append helper functions for raptor control
export async function raptorStart(): Promise<{ running: boolean }> {
  const response = await api.post<{ running: boolean }>('/raptor/start');
  return response.data;
}

export async function raptorStop(): Promise<{ running: boolean }> {
  const response = await api.post<{ running: boolean }>('/raptor/stop');
  return response.data;
}

export async function raptorStatus(): Promise<{ running: boolean; config_file?: string }> {
  const response = await api.get<{ running: boolean; config_file?: string }>('/raptor/status');
  return response.data;
}

export async function raptorLogs(maxChars = 4000): Promise<{ log_tail: string }> {
  const response = await api.post<{ log_tail: string }>('/raptor/logs', { max_chars: maxChars });
  return response.data;
}

export async function raptorDemo(value: string): Promise<{ result: string }> {
  const response = await api.get<{ result: string }>(`/raptor/demo/${encodeURIComponent(value)}`);
  return response.data;
}
