/**
 * Canonical API route prefix constants.
 * All production backend endpoints are mounted under V1_API_PREFIX.
 */
export const V1_API_PREFIX = '/api/v1' as const;
export const V1_CHAT_PREFIX = `${V1_API_PREFIX}/chat` as const;
export const V1_AUTH_PREFIX = `${V1_API_PREFIX}/auth` as const;
export const V1_PROVIDERS_PREFIX = `${V1_API_PREFIX}/providers` as const;
export const V1_HEALTH_PREFIX = `${V1_API_PREFIX}/health` as const;
export const V1_SETTINGS_PREFIX = `${V1_API_PREFIX}/settings` as const;
