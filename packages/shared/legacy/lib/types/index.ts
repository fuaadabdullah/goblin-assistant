export interface User {
  id: string;
  email: string;
  name: string;
  role?: string;
  createdAt?: string;
  updatedAt?: string;
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  sessionToken?: string;
  refreshToken?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData extends LoginCredentials {
  name: string;
}

export interface ProviderConfig {
  id: string;
  name: string;
  description: string;
  isAvailable: boolean;
  models: ModelConfig[];
}

export interface ModelConfig {
  id: string;
  name: string;
  providerId: string;
  maxTokens: number;
  description: string;
  isAvailable: boolean;
}

export interface RoutingStrategy {
  id: string;
  name: string;
  description: string;
  isDefault: boolean;
}

export interface ApiResponse<T> {
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

export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: string;
  metadata?: {
    tokens?: number;
    cost?: number;
    model?: string;
    provider?: string;
  };
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  userId: string;
}
