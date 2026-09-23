import type { User } from '../types/api';
import { supabaseUserToAppUser, authGetSession, authSignOut } from './supabase';
import { clearAuthSession } from '../utils/auth-session';
import { authMethods } from './api/auth';

export interface AuthSessionSnapshot {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
  /** Server-derived admin claim (ADMIN_EMAILS/ADMIN_DOMAINS). */
  isAdmin: boolean;
}

export const clearValidationCache = (): void => {
  // No-op: validation cache is no longer used (Supabase manages its own token state).
};

const unauthenticatedSnapshot = (): AuthSessionSnapshot => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isHydrated: true,
  isAdmin: false,
});

const readE2eAuthSnapshot = (): AuthSessionSnapshot | null => {
  if (typeof window === 'undefined') return null;

  try {
    const hostname = window.location.hostname;
    const isLocalhost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1';
    if (!isLocalhost) return null;
    if (window.localStorage.getItem('goblin_e2e_auth') !== '1') return null;
    const rawUser = window.localStorage.getItem('user_data');
    const user = rawUser ? (JSON.parse(rawUser) as User) : null;
    return {
      token: window.localStorage.getItem('auth_token') || 'mock-access-token-e2e',
      user,
      isAuthenticated: Boolean(user),
      isHydrated: true,
      isAdmin: false,
    };
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

/**
 * Resolve the admin claim server-side via the token-validation endpoint.
 *
 * The client bundle cannot see ADMIN_EMAILS/ADMIN_DOMAINS, so a Supabase user's
 * `authenticated` role is indistinguishable from an admin allowlisted only by
 * email/domain. The backend owns that check and returns it as `is_admin`.
 * Best-effort with a short timeout: the claim degrades to non-admin rather than
 * blocking session bootstrap or breaking the startup watchdog.
 */
const resolveAdminStatus = async (token: string): Promise<boolean> => {
  try {
    const result = await Promise.race([
      authMethods.validateToken(token),
      new Promise<null>((resolve) => setTimeout(() => resolve(null), 2000)),
    ]);
    return result?.is_admin === true;
  } catch {
    return false;
  }
};

/**
 * Bootstrap the auth session from the Supabase client's local session storage,
 * then attach the server-derived admin claim for client-side gating.
 */
export const bootstrapAuthSession = async (): Promise<AuthSessionSnapshot> => {
  if (typeof window === 'undefined') return unauthenticatedSnapshot();

  const e2eSnapshot = readE2eAuthSnapshot();
  if (e2eSnapshot) return e2eSnapshot;

  const { session } = await authGetSession();

  if (!session) {
    clearAuthSession();
    return unauthenticatedSnapshot();
  }

  const user = supabaseUserToAppUser(session.user);
  const isAdmin = await resolveAdminStatus(session.access_token);

  return {
    token: session.access_token,
    user,
    isAuthenticated: true,
    isHydrated: true,
    isAdmin,
  };
};

/** Convert a Supabase session into an AuthSessionSnapshot. */
export const snapshotFromSupabaseSession = (session: {
  access_token: string;
  user: Parameters<typeof supabaseUserToAppUser>[0];
}): AuthSessionSnapshot => {
  const user = supabaseUserToAppUser(session.user);
  return {
    token: session.access_token,
    user,
    isAuthenticated: true,
    isHydrated: true,
    // The login flows seed this snapshot synchronously before the server can
    // resolve the admin claim; the auth query refetches bootstrapAuthSession
    // and corrects it on the next cycle.
    isAdmin: false,
  };
};

export const clearAuthSessionState = async (): Promise<void> => {
  try {
    await authSignOut();
  } finally {
    authMethods.logout().catch(() => {
      // Backend logout failure should not prevent clearing local state.
    });
    clearAuthSession();
  }
};
