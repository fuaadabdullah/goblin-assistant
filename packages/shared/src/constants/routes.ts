/**
 * Generated from packages/shared/src/api_routes.py.
 * Do not edit by hand.
 */

export const API_PREFIX = '/api' as const;
export const API_VERSION = 'v1' as const;
export const V1_API_PREFIX = '/api/v1' as const;
export const V1_CHAT_PREFIX = '/api/v1/chat' as const;
export const V1_AUTH_PREFIX = '/api/v1/auth' as const;
export const V1_PROVIDERS_PREFIX = '/api/v1/providers' as const;
export const V1_HEALTH_PREFIX = '/api/v1/health' as const;
export const V1_SETTINGS_PREFIX = '/api/v1/settings' as const;

export const ROUTE_PREFIXES = {
  auth: '/api/v1/auth',
  chat: '/api/v1/chat',
  health: '/api/v1/health',
  providers: '/api/v1/providers',
  settings: '/api/v1/settings',
} as const;

export type SharedRoutePrefix =
  | '/api/v1'
  | '/api/v1/chat'
  | '/api/v1/auth'
  | '/api/v1/providers'
  | '/api/v1/health'
  | '/api/v1/settings';

export const buildVersionedPath = (...segments: string[]): string => {
  const cleaned = segments.map((segment) => segment.trim().replace(/^\/|\/$/g, '')).filter(Boolean);
  return cleaned.length === 0 ? V1_API_PREFIX : `${V1_API_PREFIX}/${cleaned.join('/')}`;
};
