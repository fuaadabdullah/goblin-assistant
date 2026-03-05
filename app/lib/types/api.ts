// lib/types/api.ts
import { ChatRequest, ChatResponse } from './chat';
import { ProviderConfig, ProviderHealth } from './providers';

// API Response wrapper
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: ApiError;
  meta?: {
    timestamp: string;
    requestId: string;
    version: string;
  };
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  statusCode: number;
}

// Chat API endpoints
export interface ChatApiRequest extends ChatRequest {
  sessionId: string;
}

export interface ChatApiResponse extends ApiResponse<ChatResponse> {}

// Provider API endpoints
export interface ProvidersApiResponse extends ApiResponse<ProviderConfig[]> {}

export interface ProviderHealthApiResponse extends ApiResponse<ProviderHealth[]> {}

// Search API endpoints
export interface SearchRequest {
  query: string;
  limit?: number;
  includeMetadata?: boolean;
  filters?: {
    provider?: string;
    dateRange?: {
      start: Date;
      end: Date;
    };
  };
}

export interface SearchResult {
  id: string;
  content: string;
  score: number;
  metadata?: {
    source: string;
    timestamp: Date;
    provider: string;
  };
}

export interface SearchApiResponse extends ApiResponse<SearchResult[]> {}

// Analytics API endpoints
export interface UsageStats {
  totalRequests: number;
  totalTokens: number;
  totalCost: number;
  period: {
    start: Date;
    end: Date;
  };
  breakdown: {
    byProvider: Record<string, number>;
    byModel: Record<string, number>;
    byDay: Record<string, number>;
  };
}

export interface CostBreakdown {
  totalCost: number;
  currency: string;
  breakdown: {
    byProvider: Record<string, number>;
    byModel: Record<string, number>;
    byMonth: Record<string, number>;
  };
  projections?: {
    currentMonth: number;
    nextMonth: number;
  };
}

export interface AnalyticsApiResponse extends ApiResponse<{
  usage: UsageStats;
  costs: CostBreakdown;
}> {}

// Settings API endpoints
export interface SettingsUpdateRequest {
  preferences?: Partial<import('./user').UserPreferences>;
  apiKeys?: Record<string, string>;
}

export interface SettingsApiResponse extends ApiResponse<import('./user').UserPreferences> {}

// Webhook payloads
export interface StripeWebhookPayload {
  id: string;
  object: 'event';
  type: string;
  data: {
    object: Record<string, unknown>;
  };
  created: number;
}

// Streaming types
export interface ServerSentEvent {
  event?: string;
  data: string;
  id?: string;
}

// Pagination
export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// Rate limiting
export interface RateLimitInfo {
  limit: number;
  remaining: number;
  resetTime: Date;
  retryAfter?: number;
}

export interface RateLimitedResponse extends ApiResponse {
  rateLimit: RateLimitInfo;
}
