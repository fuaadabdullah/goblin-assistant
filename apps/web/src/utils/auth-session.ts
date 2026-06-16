import type { AccessUser } from './access';

const SESSION_TOKEN_COOKIE = 'session_token';
const REFRESH_TOKEN_COOKIE = 'refresh_token';
const LEGACY_TOKEN_COOKIES = ['auth_token', 'goblin_auth', 'goblin_admin'];

const clearCookie = (name: string): void => {
  if (typeof document === 'undefined') return;
  document.cookie = `${name}=; Path=/; Max-Age=0`;
};

interface PersistAuthInput {
  token?: string | null | undefined;
  refreshToken?: string | null | undefined;
  user?: AccessUser | null | undefined;
  expiresIn?: number | null | undefined;
}

/**
 * Persist non-sensitive user data to localStorage for UI hydration.
 * Session cookies are managed by @supabase/ssr — nothing to write here.
 */
export const persistAuthSession = ({ user }: PersistAuthInput): void => {
  if (typeof window === 'undefined') return;
  if (user) {
    localStorage.setItem('user_data', JSON.stringify(user));
  }
};

/**
 * Retrieve the stored auth token (legacy localStorage fallback only).
 * Session is now managed by @supabase/ssr cookies — this exists for the
 * Zustand authStore bootstrap path until that store is removed.
 */
export const getAuthToken = (): string | null => {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|;\\s*)${SESSION_TOKEN_COOKIE}=([^;]*)`),
  );
  if (match?.[1]) return decodeURIComponent(match[1]);
  return localStorage.getItem('auth_token');
};

export const getRefreshToken = (): string | null => {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(
    new RegExp(`(?:^|;\\s*)${REFRESH_TOKEN_COOKIE}=([^;]*)`),
  );
  if (match?.[1]) return decodeURIComponent(match[1]);
  return null;
};

export const clearAuthSession = (): void => {
  if (typeof window === 'undefined') return;
  localStorage.removeItem('auth_token');
  localStorage.removeItem('user_data');
  // Clear legacy flag cookies and any leftover backend-set cookies
  [SESSION_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE, ...LEGACY_TOKEN_COOKIES].forEach(clearCookie);
};
