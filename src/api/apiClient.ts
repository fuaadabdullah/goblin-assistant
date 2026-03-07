/**
 * Backward-compatible API client entrypoint.
 *
 * Canonical implementation now lives in `src/lib/api.ts` (Axios + typed methods).
 */
export {
  apiClient,
} from '../lib/api';

export type {
  ProviderUpdatePayload,
  PasskeyCredential,
  SandboxRunPayload,
  AccountProfile,
  AccountPreferences,
} from '../lib/api';
