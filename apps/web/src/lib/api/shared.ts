/**
 * API Client — Shared Barrel
 *
 * This file re-exports everything from the modular API infrastructure.
 * It exists for backward compatibility so existing importers continue to work.
 *
 * Prefer importing from the focused modules directly for new code:
 *   - ./api-types    → Types and interfaces
 *   - ./http-client  → Axios instances, auth interceptor, constants
 *   - ./http-helpers → HTTP verb wrappers, error handling
 *   - ./retry        → withTransientRetry
 *   - ./csrf         → CSRF token management
 */

// Re-export all types (backward-compatible for type-only imports)
export type {
  ProviderUpdatePayload,
  PasskeyCredential,
  SandboxRunPayload,
  AccountProfile,
  AccountPreferences,
  ConversationCreateResponse,
  ConversationInfoResponse,
  ConversationDetailResponse,
  ConversationSendResponse,
  StandardApiErrorPayload,
  StandardApiEnvelope,
  DomainChatMessage,
  ChatUsage,
  ChatMessage,
  ChatCompletionResponse,
  HealthStatus,
  ValidateTokenResponse,
} from './api-types';

// Re-export all values and types from http-client
export {
  AUTH_REQUEST_TIMEOUT_MS,
  V1_API_PREFIX,
  V1_CHAT_PREFIX,
  backendHttp,
  frontendHttp,
  refreshAccessToken,
  withAuth,
} from './http-client';

// Re-export all values and types from http-helpers
export {
  extractApiErrorMessage,
  normalizeAxiosError,
  unwrapEnvelope,
  assertNoVersionedClientPath,
  getBackend,
  postBackend,
  putBackend,
  patchBackend,
  deleteBackend,
  getFrontend,
  postFrontend,
  devWarn,
} from './http-helpers';

// Re-export retry logic
export { withTransientRetry } from './retry';

// Re-export CSRF token management
export { prefetchCsrfToken, getCsrfToken } from './csrf';
