import { API_PROXY_ROUTES, type ApiProxyRoute } from '@goblin/shared';

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
  let resolved: ApiProxyRoute | null = null;

  for (const route of API_PROXY_ROUTES) {
    if (!isPrefixMatch(normalizedPathname, route.frontendPrefix)) {
      continue;
    }

    if (!resolved || route.frontendPrefix.length > resolved.frontendPrefix.length) {
      resolved = route;
    }
  }

  return resolved;
};
