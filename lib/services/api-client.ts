'use client';

import { handleApiError } from '../error-handler';

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    statusCode: number;
  };
  meta?: {
    timestamp: string;
    requestId: string;
    version: string;
  };
}

class ApiClient {
  private baseUrl: string;
  private authToken: string | null = null;

  constructor(baseUrl: string = '/api') {
    this.baseUrl = baseUrl;
  }

  // Auth token management
  setAuthToken(token: string) {
    this.authToken = token;
  }

  clearAuthToken() {
    this.authToken = null;
  }

  getAuthToken() {
    return this.authToken;
  }

  private async request<T>(
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    endpoint: string,
    data?: unknown,
    params?: Record<string, string>
  ): Promise<ApiResponse<T>> {
    try {
      // Build URL with query parameters
      const url = new URL(`${this.baseUrl}${endpoint}`, window.location.origin);

      if (params) {
        Object.entries(params).forEach(([key, value]) => {
          url.searchParams.append(key, value);
        });
      }

      // Build request options
      const options: RequestInit = {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        credentials: 'include',
      };

      if (method !== 'GET' && data) {
        options.body = JSON.stringify(data);
      }

      // Make the request
      const response = await fetch(url.toString(), options);

      if (!response.ok) {
        // Try to parse error response
        try {
          const errorData = await response.json();
          return {
            success: false,
            error: {
              code: errorData.error?.code || 'HTTP_ERROR',
              message: errorData.error?.message || `HTTP ${response.status}`,
              statusCode: response.status,
            },
            meta: {
              timestamp: new Date().toISOString(),
              requestId: Math.random().toString(36).substring(7),
              version: '1.0',
            },
          };
        } catch {
          return {
            success: false,
            error: {
              code: 'HTTP_ERROR',
              message: `HTTP ${response.status}`,
              statusCode: response.status,
            },
            meta: {
              timestamp: new Date().toISOString(),
              requestId: Math.random().toString(36).substring(7),
              version: '1.0',
            },
          };
        }
      }

      // Parse successful response
      const responseData = await response.json();

      return {
        success: true,
        data: responseData,
        meta: {
          timestamp: new Date().toISOString(),
          requestId: Math.random().toString(36).substring(7),
          version: '1.0',
        },
      };
    } catch (error) {
      console.error('API Client Error:', error);

      return {
        success: false,
        error: {
          code: 'NETWORK_ERROR',
          message: error instanceof Error ? error.message : 'Network error occurred',
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

  async get<T>(endpoint: string, params?: Record<string, string>): Promise<ApiResponse<T>> {
    return this.request<T>('GET', endpoint, undefined, params);
  }

  async post<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>('POST', endpoint, data);
  }

  async put<T>(endpoint: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>('PUT', endpoint, data);
  }

  async delete<T>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>('DELETE', endpoint);
  }

  // Streaming support (mock implementation)
  stream(endpoint: string): AsyncIterable<unknown> {
    console.log('API Client stream called with:', endpoint);
    // Mock streaming implementation
    return {
      [Symbol.asyncIterator]: async function* () {
        for (let i = 0; i < 3; i++) {
          yield { chunk: `Mock chunk ${i + 1}`, index: i };
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      },
    };
  }

  // WebSocket support (mock implementation)
  connectWebSocket(endpoint: string): WebSocket {
    console.log('API Client connectWebSocket called with:', endpoint);
    // Mock WebSocket implementation
    const mockWs = {
      onopen: () => console.log('Mock WebSocket opened'),
      onmessage: (event: any) => console.log('Mock WebSocket message:', event),
      onerror: (event: any) => console.error('Mock WebSocket error:', event),
      onclose: () => console.log('Mock WebSocket closed'),
      send: (data: any) => console.log('Mock WebSocket send:', data),
      close: () => console.log('Mock WebSocket closed'),
    };
    return mockWs as unknown as WebSocket;
  }
}

// Singleton instance
export const apiClient = new ApiClient();
