import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { toast } from 'react-hot-toast';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8004';

// Request/Response interceptors
interface ApiClientOptions {
  baseURL?: string;
  timeout?: number;
  withCredentials?: boolean;
}

class ApiClient {
  private client: AxiosInstance;

  constructor(options: ApiClientOptions = {}) {
    this.client = axios.create({
      baseURL: options.baseURL || API_BASE_URL,
      timeout: options.timeout || 10000,
      withCredentials: options.withCredentials || true,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        return response;
      },
      (error) => {
        this.handleApiError(error);
        return Promise.reject(error);
      }
    );
  }

  private handleApiError(error: any) {
    if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const message = error.response.data?.message || 'An error occurred';

      switch (status) {
        case 401:
          // Unauthorized - redirect to login
          localStorage.removeItem('auth_token');
          toast.error('Session expired. Please log in again.');
          window.location.href = '/login';
          break;
        case 403:
          toast.error('Access denied');
          break;
        case 404:
          toast.error('Resource not found');
          break;
        case 500:
          toast.error('Server error. Please try again later.');
          break;
        default:
          toast.error(message);
      }
    } else if (error.request) {
      // Network error
      toast.error('Network error. Please check your connection.');
    } else {
      // Other error
      toast.error('An unexpected error occurred.');
    }
  }

  // HTTP methods
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  // File upload method
  async upload<T>(url: string, file: any, onProgress?: (progress: number) => void): Promise<T> {
    const formData = new FormData();
    formData.append('file', file);

    const config: AxiosRequestConfig = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    };

    if (onProgress) {
      config.onUploadProgress = (progressEvent) => {
        const progressPercent = Math.round((progressEvent.loaded * 100) / progressEvent.total!);
        onProgress(progressPercent);
      };
    }

    const response = await this.client.post<T>(url, formData, config);
    return response.data;
  }

  // Set auth token
  setAuthToken(token: string | null) {
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  // Get auth token
  getAuthToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  // Clear auth
  clearAuth() {
    this.setAuthToken(null);
  }
}

// Create singleton instance
export const apiClient = new ApiClient();

// API endpoints
export const apiEndpoints = {
  // Auth
  auth: {
    login: '/api/auth/login',
    register: '/api/auth/register',
    logout: '/api/auth/logout',
    refresh: '/api/auth/refresh',
    me: '/api/auth/me',
  },
  
  // Chat
  chat: {
    messages: '/api/chat/messages',
    stream: '/api/chat/stream',
    history: '/api/chat/history',
    clear: '/api/chat/clear',
  },
  
  // Providers
  providers: {
    list: '/api/providers',
    health: '/api/providers/health',
    settings: '/api/providers/settings',
  },
  
  // Analytics
  analytics: {
    usage: '/api/analytics/usage',
    costs: '/api/analytics/costs',
    providers: '/api/analytics/providers',
  },
  
  // Settings
  settings: {
    user: '/api/settings/user',
    theme: '/api/settings/theme',
    preferences: '/api/settings/preferences',
    settings: '/api/settings/providers',
  },
} as const;

export default apiClient;
