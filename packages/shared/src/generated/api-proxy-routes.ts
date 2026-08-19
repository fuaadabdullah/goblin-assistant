/**
 * Generated from packages/shared/src/api_proxy_routes.py and packages/sdk/openapi/routes.json.
 * Do not edit by hand.
 */

export const API_PROXY_ROUTES = [
  { frontendPrefix: '/api/account', backendPrefix: '/api/v1/account' },
  { frontendPrefix: '/api/agent', backendPrefix: '/api/v1/agent' },
  { frontendPrefix: '/api/auth', backendPrefix: '/api/v1/auth' },
  { frontendPrefix: '/api/chat', backendPrefix: '/api/v1/chat' },
  { frontendPrefix: '/api/costs', backendPrefix: '/api/v1/routing/costs' },
  { frontendPrefix: '/api/feedback', backendPrefix: '/api/v1/api/feedback' },
  { frontendPrefix: '/api/health/routing', backendPrefix: '/api/v1/health/routing' },
  { frontendPrefix: '/api/health/streaming', backendPrefix: '/api/v1/health/streaming' },
  { frontendPrefix: '/api/metrics', backendPrefix: '/metrics' },
  { frontendPrefix: '/api/raptor', backendPrefix: '/api/v1/raptor' },
  { frontendPrefix: '/api/routing', backendPrefix: '/api/v1/routing' },
  { frontendPrefix: '/api/runtime', backendPrefix: '/api/v1/api' },
  { frontendPrefix: '/api/sandbox', backendPrefix: '/api/v1/sandbox' },
  { frontendPrefix: '/api/search', backendPrefix: '/api/v1/search' },
  { frontendPrefix: '/api/settings', backendPrefix: '/api/v1/settings' },
  { frontendPrefix: '/api/support', backendPrefix: '/api/v1/support' },
] as const;

export type ApiProxyRoute = (typeof API_PROXY_ROUTES)[number];

export const API_PROXY_EXPLICIT_PATHS = [
  '/api/debug/model-usage',
  '/api/errors',
  '/api/generate',
  '/api/health',
  '/api/models',
  '/api/system-status',
] as const;

export type ApiProxyExplicitPath = (typeof API_PROXY_EXPLICIT_PATHS)[number];
