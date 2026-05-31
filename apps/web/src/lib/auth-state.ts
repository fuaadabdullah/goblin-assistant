import type { User, ValidateTokenResponse } from '../types/api';
import { apiClient } from './api';
import {
  clearAuthSession,
  getAuthToken,
  isAuthenticated as checkAuth,
  persistAuthSession,
} from '../utils/auth-session';

export interface AuthSessionSnapshot {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
}

// Token validation cache with TTL (1 hour)
const TOKEN_CACHE_TTL_MS = 60 * 60 * 1000;
interface CachedValidation {
  payload: ValidateTokenResponse;
  timestamp: number;
}
const validationCache = new Map<string, CachedValidation>();

const getCachedValidation = (token: string): ValidateTokenResponse | null => {
  const cached = validationCache.get(token);
  if (!cached) return null;
  if (Date.now() - cached.timestamp > TOKEN_CACHE_TTL_MS) {
    validationCache.delete(token);
    return null;
  }
  return cached.payload;
};

const setCachedValidation = (token: string, payload: ValidateTokenResponse): void => {
  validationCache.set(token, { payload, timestamp: Date.now() });
};

export const clearValidationCache = (): void => {
  validationCache.clear();
};

const unauthenticatedSnapshot = (): AuthSessionSnapshot => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isHydrated: true,
});

const safeJsonParse = (value: string | null): unknown => {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
};

export const hasRole = (user: User | null | undefined, role: string): boolean => {
  if (!user) return false;
  return user.role === role || Boolean(user.roles?.includes(role));
};

export const hasAnyRole = (user: User | null | undefined, roles: string[]): boolean => {
  if (!user) return false;
  return roles.some((role) => hasRole(user, role));
};

const readStoredSession = (): { token: string | null; user: User | null } => {
  const token = getAuthToken();
  const user = safeJsonParse(window.localStorage.getItem('user_data')) as User | null;
  return { token, user };
};

const resolveValidatedUser = (
  payload: ValidateTokenResponse,
  fallbackUser: User | null
): User | null => {
  const candidateUser = payload?.user ?? null;
  return candidateUser && typeof candidateUser === 'object' && 'id' in candidateUser
    ? candidateUser
    : fallbackUser;
};

const getErrorStatus = (error: unknown): number | undefined => {
  if (typeof error !== 'object' || error === null || !('status' in error)) return undefined;
  return Number((error as { status?: unknown }).status);
};

const isHardAuthFailure = (status: number | undefined): boolean =>
  status === 401 || status === 403;

export const bootstrapAuthSession = async (): Promise<AuthSessionSnapshot> => {
  if (typeof window === 'undefined') {
    return unauthenticatedSnapshot();
  }

  // Migration: goblin_auth cookie is present but auth_token is also in localStorage.
  // The user has re-authenticated via HttpOnly cookies — the localStorage copy is stale.
  if (checkAuth() && window.localStorage.getItem('auth_token')) {
    window.localStorage.removeItem('auth_token');
  }

  const { token: storedToken, user: storedUser } = readStoredSession();

  // HttpOnly cookie path: JWT lives in an HttpOnly cookie the backend set.
  // No JS-readable token exists, but goblin_auth=1 confirms the session.
  // We trust the flag here; the backend will reject stale cookies on real requests.
  if (!storedToken && checkAuth()) {
    return {
      token: null,
      user: storedUser,
      isAuthenticated: true,
      isHydrated: true,
    };
  }

  if (!storedToken) {
    return unauthenticatedSnapshot();
  }

  // Legacy localStorage token path: validate with backend.
  try {
    let payload = getCachedValidation(storedToken);
    if (!payload) {
      payload = (await apiClient.validateToken(storedToken)) as ValidateTokenResponse;
      setCachedValidation(storedToken, payload);
    }

    if (payload?.valid === false) {
      clearAuthSession();
      return unauthenticatedSnapshot();
    }

    const validatedUser = resolveValidatedUser(payload, storedUser);
    if (!validatedUser) {
      return { token: storedToken, user: storedUser, isAuthenticated: Boolean(storedUser), isHydrated: true };
    }

    persistAuthSession({
      token: storedToken,
      user: validatedUser,
      expiresIn: payload?.expires_in,
    });

    return { token: storedToken, user: validatedUser, isAuthenticated: true, isHydrated: true };
  } catch (error) {
    const status = getErrorStatus(error);
    if (isHardAuthFailure(status)) {
      clearAuthSession();
      return unauthenticatedSnapshot();
    }

    // Fail closed on network/validation errors — prevents route-bypass UX.
    clearAuthSession();
    return unauthenticatedSnapshot();
  }
};

export const clearAuthSessionState = async (): Promise<void> => {
  try {
    await apiClient.logout();
  } catch {
    // Best-effort remote logout; local clear always proceeds.
  }

  clearValidationCache();
  clearAuthSession();
};
