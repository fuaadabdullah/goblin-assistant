// lib/services/api-client.ts
import type { ApiResponse, ApiError } from '../types';

class ApiClient {
  private baseURL: string;
  private defaultHeaders: Record<string, string>;

  constructor(baseURL?: string) {
    this.baseURL = baseURL || (typeof window !== 'undefined' ? '' : process.env.BACKEND_URL || 'http://localhost:8003');
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  private getAuthToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('auth-token');
    }
    return null;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseURL}${endpoint}`;

    const headers: Record<string, string> = {
      ...this.defaultHeaders,
    };

    // Add custom headers if provided
    if (options.headers) {
      Object.entries(options.headers).forEach(([key, value]) => {
        headers[key] = String(value);
      });
    }

    const authToken = this.getAuthToken();
    if (authToken) {
      headers.Authorization = `Bearer ${authToken}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      let data: T | undefined;
      let error: ApiError | undefined;

      try {
        const responseData = await response.json();

        if (response.ok) {
          data = responseData;
        } else {
          error = {
            code: responseData.code || `HTTP_${response.status}`,
            message: responseData.message || 'Request failed',
            details: responseData.details,
            statusCode: response.status,
          };
        }
      } catch {
        // If response is not JSON, create a generic error
        error = {
          code: `HTTP_${response.status}`,
          message: response.statusText || 'Request failed',
          statusCode: response.status,
        };
      }

      return {
        success: response.ok,
        data,
        error,
        meta: {
          timestamp: new Date().toISOString(),
          requestId: Math.random().toString(36).substring(7),
          version: '1.0',
        },
      };
    } catch (networkError) {
      return {
        success: false,
        error: {
          code: 'NETWORK_ERROR',
          message: networkError instanceof Error ? networkError.message : 'Network request failed',
          statusCode: 0,
        },
        meta: {
          timestamp: new Date().toISOString(),
          requestId: Math.random().toString(36).substring(7),
          version: '1.0',
        },
      };
    }
  }

  // GET request
  async get<T>(endpoint: string, params?: Record<string, string>): Promise<ApiResponse<T>> {
    const url = params
      ? `${endpoint}?${new URLSearchParams(params)}`
      : endpoint;

    return this.request<T>(url, { method: 'GET' });
  }

  // POST request
  async post<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // PUT request
  async put<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // DELETE request
  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // PATCH request
  async patch<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  // SSE streaming
  async *stream(endpoint: string, data?: unknown): AsyncGenerator<unknown, void, unknown> {
    const url = `${this.baseURL}${endpoint}`;

    const headers = {
      ...this.defaultHeaders,
    };

    const authToken = this.getAuthToken();
    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      throw new Error(`Streaming request failed: ${response.statusText}`);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('Response body is not readable');
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const decoder = new (globalThis as any).TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') return;

            try {
              yield JSON.parse(data);
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }

  // WebSocket connection
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  connectWebSocket(endpoint: string): any {
    const protocol = this.baseURL.startsWith('https') ? 'wss' : 'ws';
    const baseUrl = this.baseURL.replace(/^https?/, '');
    const wsUrl = `${protocol}${baseUrl}${endpoint}`;

    const authToken = this.getAuthToken();
    const url = authToken ? `${wsUrl}?token=${authToken}` : wsUrl;

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return new (globalThis as any).WebSocket(url);
  }

  // Set auth token
  setAuthToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('auth-token', token);
    }
  }

  // Clear auth token
  clearAuthToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('auth-token');
    }
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for testing or multiple instances
export { ApiClient };