import type { User, ValidateTokenResponse } from '../types/api';
import { apiClient } from './api';
import { clearAuthSession, getAuthToken, isAuthenticated as checkAuth, persistAuthSession } from '../utils/auth-session';

export interface AuthSessionSnapshot {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
}

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
  return roles.some(role => hasRole(user, role));
};

const provisionalSnapshot = (token: string, user: User | null): AuthSessionSnapshot => ({
  token,
  user,
  isAuthenticated: Boolean(token && user && typeof user === 'object' && 'id' in user),
  isHydrated: true,
});

const readStoredSession = (): { token: string | null; user: User | null } => {
  const token = getAuthToken();
  const user = safeJsonParse(window.localStorage.getItem('user_data')) as User | null;
  return { token, user };
};

const resolveValidatedUser = (
  payload: ValidateTokenResponse,
  fallbackUser: User | null,
): User | null => {
  const candidateUser = payload?.user ?? null;
  return candidateUser && typeof candidateUser === 'object' && 'id' in candidateUser
    ? candidateUser
    : fallbackUser;
};

const getErrorStatus = (error: unknown): number | undefined => {
  if (typeof error !== 'object' || error === null || !('status' in error)) {
    return undefined;
  }
  return Number((error as { status?: unknown }).status);
};

const isHardAuthFailure = (status: number | undefined): boolean =>
  status === 401 || status === 403;

export const bootstrapAuthSession = async (): Promise<AuthSessionSnapshot> => {
  if (typeof window === 'undefined') {
    return unauthenticatedSnapshot();
  }

  const { token: storedToken, user: storedUser } = readStoredSession();

  // HttpOnly cookie path: no JS-readable token but auth flag is set.
  if (!storedToken && checkAuth()) {
    return provisionalSnapshot('httponly', storedUser);
  }

  if (!storedToken) {
    return unauthenticatedSnapshot();
  }

  try {
    const payload = (await apiClient.validateToken(storedToken)) as ValidateTokenResponse;

    if (payload?.valid === false) {
      clearAuthSession();
      return unauthenticatedSnapshot();
    }

    const validatedUser = resolveValidatedUser(payload, storedUser);
    if (!validatedUser) {
      return provisionalSnapshot(storedToken, storedUser);
    }

    persistAuthSession({
      token: storedToken,
      user: validatedUser,
      expiresIn: payload?.expires_in,
    });

    return provisionalSnapshot(storedToken, validatedUser);
  } catch (error) {
    const status = getErrorStatus(error);
    if (isHardAuthFailure(status)) {
      clearAuthSession();
      return unauthenticatedSnapshot();
    }

    // Fail closed on validation/network errors to avoid route/login bypass UX.
    // Users can sign in again and refresh the session deterministically.
    clearAuthSession();
    return unauthenticatedSnapshot();
  }
};

export const clearAuthSessionState = async (): Promise<void> => {
  try {
    await apiClient.logout();
  } catch {
    // Best-effort remote logout; local clear still proceeds.
  }

  clearAuthSession();
};
