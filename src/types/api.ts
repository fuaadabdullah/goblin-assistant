// Shared API types to replace `any` usage

/**
 * Generic API response wrapper
 */
export interface ApiResponse<T = unknown> {
  data: T;
  status: number;
  message?: string;
  success: boolean;
}

/**
 * Generic API result with error handling
 */
export type ApiResult<T> = 
  | { ok: true; data: T }
  | { ok: false; error: string; code?: number };

/**
 * API error interface
 */
export interface ApiError {
  message: string;
  code?: number;
  status?: number;
  details?: unknown;
}

/**
 * Pagination interface
 */
export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
}

export interface PaginatedResponse<T> extends ApiResponse<T> {
  pagination?: {
    page: number;
    limit: number;
    total: number;
    hasMore: boolean;
  };
}

/**
 * Type guard to check if response is an error
 */
export function isApiError(x: unknown): x is ApiError {
  return !!x && typeof x === 'object' && 'message' in x;
}

/**
 * Type guard to check if API response indicates success
 */
export function isApiSuccess<T>(response: ApiResponse<T>): response is ApiResponse<T> & { data: T } {
  return response.success === true && response.status >= 200 && response.status < 300;
}

/**
 * Safe JSON parse with error handling
 */
export async function safeJsonParse(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}