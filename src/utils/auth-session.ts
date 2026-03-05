import { isAdminUser, type AccessUser } from './access';

const AUTH_FLAG_COOKIE = 'goblin_auth';
const ADMIN_COOKIE = 'goblin_admin';
const SESSION_TOKEN_COOKIE = 'session_token';
const LEGACY_TOKEN_COOKIES = ['auth_token'];
const DEFAULT_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

const cookieBase = (maxAge?: number): string => {
  const parts = ['Path=/', 'SameSite=Lax'];
  if (typeof maxAge === 'number' && Number.isFinite(maxAge)) {
    parts.push(`Max-Age=${Math.max(0, Math.floor(maxAge))}`);
  }
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    parts.push('Secure');
  }
  return parts.join('; ');
};

const setCookie = (name: string, value: string, maxAge?: number): void => {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=${encodeURIComponent(value)}; ${cookieBase(maxAge)}`;
};

const clearCookie = (name: string): void => {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=; Path=/; Max-Age=0`;
};

interface PersistAuthInput {
  token?: string | null;
  user?: AccessUser | null;
  expiresIn?: number | null;
}

/**
 * Persist authentication session.
 *
 * Stores the JWT in a `session_token` cookie (readable by middleware) instead
 * of localStorage to reduce XSS exposure. Also sets the legacy `goblin_auth=1`
 * flag for backward compatibility with the middleware route guard.
 *
 * TODO: Once the backend sets httpOnly cookies directly on login/refresh
 * responses, remove the client-side cookie writes entirely and only keep
 * the user_data localStorage entry for UI display.
 */
export const persistAuthSession = ({ token, user, expiresIn }: PersistAuthInput): void => {
  if (typeof window === 'undefined') return;

  const maxAge =
    typeof expiresIn === 'number' && Number.isFinite(expiresIn)
      ? Math.max(0, expiresIn)
      : DEFAULT_MAX_AGE_SECONDS;

  if (token) {
    // Store token in a cookie (accessible to middleware) instead of localStorage
    setCookie(SESSION_TOKEN_COOKIE, token, maxAge);
    // Keep the legacy flag for middleware backward compatibility
    setCookie(AUTH_FLAG_COOKIE, '1', maxAge);
  }

  if (user) {
    // User data is non-sensitive display info — localStorage is fine here
    localStorage.setItem('user_data', JSON.stringify(user));
    setCookie(ADMIN_COOKIE, isAdminUser(user) ? '1' : '0', maxAge);
  }
};

/**
 * Retrieve the stored auth token (checks cookie, falls back to legacy localStorage).
 */
export const getAuthToken = (): string | null => {
  if (typeof document === 'undefined') return null;
  // Try cookie first
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${SESSION_TOKEN_COOKIE}=([^;]*)`));
  if (match?.[1]) return decodeURIComponent(match[1]);
  // Legacy fallback — needed until all users re-authenticate
  return localStorage.getItem('auth_token');
};

export const clearAuthSession = (): void => {
  if (typeof window === 'undefined') return;

  localStorage.removeItem('auth_token');
  localStorage.removeItem('user_data');

  clearCookie(AUTH_FLAG_COOKIE);
  clearCookie(ADMIN_COOKIE);
  clearCookie(SESSION_TOKEN_COOKIE);
  LEGACY_TOKEN_COOKIES.forEach(clearCookie);
};
