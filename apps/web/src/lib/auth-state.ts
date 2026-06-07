import type { User } from '../types/api';
import { supabase, supabaseUserToAppUser } from './supabase';
import { clearAuthSession } from '../utils/auth-session';

export interface AuthSessionSnapshot {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isHydrated: boolean;
}

export const clearValidationCache = (): void => {
  // No-op: validation cache is no longer used (Supabase manages its own token state).
};

const unauthenticatedSnapshot = (): AuthSessionSnapshot => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isHydrated: true,
});

export const hasRole = (user: User | null | undefined, role: string): boolean => {
  if (!user) return false;
  return user.role === role || Boolean(user.roles?.includes(role));
};

export const hasAnyRole = (user: User | null | undefined, roles: string[]): boolean => {
  if (!user) return false;
  return roles.some((role) => hasRole(user, role));
};

/**
 * Bootstrap the auth session from the Supabase client's local session storage.
 * This is synchronous in practice — Supabase reads from localStorage, no network call.
 */
export const bootstrapAuthSession = async (): Promise<AuthSessionSnapshot> => {
  if (typeof window === 'undefined') return unauthenticatedSnapshot();

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    clearAuthSession();
    return unauthenticatedSnapshot();
  }

  return {
    token: session.access_token,
    user: supabaseUserToAppUser(session.user),
    isAuthenticated: true,
    isHydrated: true,
  };
};

export const clearAuthSessionState = async (): Promise<void> => {
  try {
    await supabase.auth.signOut();
  } finally {
    clearAuthSession();
  }
};
