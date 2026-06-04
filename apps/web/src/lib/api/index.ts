/**
 * API Client
 *
 * This is the main barrel export for the API client. It composes all domain-specific
 * methods (chat, auth, providers, etc.) into a single `apiClient` object that's used
 * throughout the frontend.
 *
 * Structure:
 * - shared.ts: Shared infrastructure (axios config, auth, error handling, HTTP helpers)
 * - chat.ts: Conversation and message endpoints
 * - auth.ts: Authentication endpoints
 * - providers.ts: Provider management endpoints
 * - generation.ts: Generation endpoints
 * - health.ts: Health check endpoints
 * - sandbox.ts: Sandbox operation endpoints
 * - account.ts: Account management endpoints
 * - search.ts: Search endpoints
 * - logging.ts: Logging endpoints
 * - support.ts: Support endpoints
 */

import { chatMethods } from './chat';
import { authMethods } from './auth';
import { providersMethods } from './providers';
import { generationMethods } from './generation';
import { healthMethods } from './health';
import { sandboxMethods } from './sandbox';
import { accountMethods } from './account';
import { searchMethods } from './search';
import { loggingMethods } from './logging';
import { supportMethods } from './support';
import { runtimeMethods } from './runtime';

// Export all shared types and utilities
export * from './shared';

// Compose and export the main apiClient
export const apiClient = {
  // Chat methods
  ...chatMethods,

  // Auth methods
  ...authMethods,

  // Providers methods
  ...providersMethods,

  // Generation methods
  ...generationMethods,

  // Health methods
  ...healthMethods,

  // Sandbox methods
  ...sandboxMethods,

  // Account methods
  ...accountMethods,

  // Search methods
  ...searchMethods,

  // Logging methods
  ...loggingMethods,

  // Support methods
  ...supportMethods,

  // Runtime/orchestration methods
  ...runtimeMethods,
};

export type ApiClient = typeof apiClient;
