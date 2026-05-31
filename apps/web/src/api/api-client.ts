/**
 * Thin adapter over the canonical apiClient.
 *
 * All HTTP, retry, auth, and error logic lives in src/lib/api/.
 * This file exists only to preserve the public exports that callers
 * already import from '@/api'. New code should import from '@/lib/api'
 * or '@/lib/provider-keys' directly.
 */

import {
  apiClient,
  deleteBackend,
  getBackend,
  postBackend,
  putBackend,
  patchBackend,
} from '@/lib/api';
import { runtimeClient, runtimeClientDemo } from '@/lib/api/runtimeClient';

// Re-export shared types consumed from '@/api'
export type {
  ProviderUpdatePayload,
  PasskeyCredential,
  SandboxRunPayload,
  AccountProfile,
  AccountPreferences,
} from '@/lib/api';

// Re-export apiClient for callers that import it from '@/api'
export { apiClient };

export { runtimeClient, runtimeClientDemo };

// ---------------------------------------------------------------------------
// api: minimal HTTP shim backed by the canonical axios helpers.
// Used only by raptor.ts — new code should call getBackend/postBackend directly.
// ---------------------------------------------------------------------------

export const api = {
  get: async <T>(path: string) => ({ data: await getBackend<T>(path) }),
  post: async <T = unknown>(path: string, body?: unknown) => ({
    data: await postBackend<T>(path, body),
  }),
  put: async <T = unknown>(path: string, body?: unknown) => ({
    data: await putBackend<T>(path, body),
  }),
  patch: async <T = unknown>(path: string, body?: unknown) => ({
    data: await patchBackend<T>(path, body),
  }),
  delete: async <T = unknown>(path: string) => ({
    data: await deleteBackend<T>(path),
  }),
};
