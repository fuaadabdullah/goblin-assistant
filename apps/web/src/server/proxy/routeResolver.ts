import {
  API_PROXY_ENDPOINT_ROUTES,
  API_PROXY_PREFIX_ROUTES,
  type ApiProxyRoute,
} from '@goblin/shared';

const normalizePathname = (pathname: string): string =>
  pathname !== '/' ? pathname.replace(/\/+$/, '') : pathname;

const isPrefixMatch = (pathname: string, prefix: string): boolean =>
  pathname === prefix || pathname.startsWith(`${prefix}/`);

const pathSegmentCount = (pathname: string): number => pathname.split('/').filter(Boolean).length;

export const pathSegmentsToPathname = (segments: readonly string[]): string =>
  segments.length === 0 ? '/api' : `/api/${segments.join('/')}`;

export const suffixFromSegments = (segments: readonly string[], frontendPrefix: string): string => {
  const prefixSegments = Math.max(pathSegmentCount(frontendPrefix) - 1, 0);
  return segments.slice(prefixSegments).join('/');
};

export const resolveProxyRoute = (pathname: string): ApiProxyRoute | null => {
  const normalizedPathname = normalizePathname(pathname);

  // Endpoint routes: exact match, checked first — no sub-path forwarding.
  for (const route of API_PROXY_ENDPOINT_ROUTES) {
    if (normalizedPathname === normalizePathname(route.frontendPath)) {
      return { ...route, kind: 'endpoint' };
    }
  }

  // Prefix routes: longest-prefix match wins.
  let resolved: (typeof API_PROXY_PREFIX_ROUTES)[number] | null = null;
  for (const route of API_PROXY_PREFIX_ROUTES) {
    if (!isPrefixMatch(normalizedPathname, route.frontendPrefix)) continue;
    if (!resolved || route.frontendPrefix.length > resolved.frontendPrefix.length) {
      resolved = route;
    }
  }

  return resolved ? { ...resolved, kind: 'prefix' } : null;
};
