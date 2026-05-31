import { create } from 'zustand';
import { devWarn } from '../utils/dev-log';
import type { User } from '../types/api';
import type { ValidateTokenResponse } from '../types/api';
import {
  clearAuthSession,
  getAuthToken,
  isAuthenticated as checkAuth,
  persistAuthSession,
} from '../utils/auth-session';
import { apiClient } from '@/lib/api';

type SessionInput = {
  token: string;
  refreshToken?: string | null;
  user: User;
  expiresIn?: number | null;
};

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isHydrated: boolean;
  bootstrapFromSession: () => Promise<void>;
  setSession: (input: SessionInput) => void;
  clearSession: () => void;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
}

const safeJsonParse = (value: string | null): unknown => {
  if (!value) return null;
  try {
    return JSON.parse(value);
  } catch (e) {
    // Log parse errors to help identify data corruption
    devWarn('Failed to parse stored user data', e);
    return null;
  }
};

let bootstrapPromise: Promise<void> | null = null;

/**
 * Single source of truth for auth state.
 *
 * Persistence lives in `utils/auth-session` (localStorage + cookies).
 * Next.js middleware is the routing gate; this store is for client state only.
 */
export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,
  isHydrated: false,

  setSession: ({ token, refreshToken, user, expiresIn }: SessionInput) => {
    persistAuthSession({ token, refreshToken, user, expiresIn });
    set({
      token,
      user,
      isAuthenticated: Boolean(token && user),
      isHydrated: true,
      isLoading: false,
    });
  },

  clearSession: () => {
    clearAuthSession();
    set({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },

  bootstrapFromSession: async () => {
    if (typeof window === 'undefined') {
      set({ isHydrated: true, isLoading: false });
      return;
    }

    if (bootstrapPromise) return bootstrapPromise;
    if (get().isHydrated || get().isLoading) {
      set({ isHydrated: true, isLoading: false });
      return;
    }

    bootstrapPromise = (async () => {
      set({ isLoading: true });

      const storedToken = getAuthToken();
      const hasSession = checkAuth();
      const storedUserDataRaw = window.localStorage.getItem('user_data');
      const storedUser = safeJsonParse(storedUserDataRaw) as User | null;

      // No JS-readable token AND no auth flag cookie → not authenticated.
      if (!storedToken && !hasSession) {
        set({ isHydrated: true, isLoading: false });
        return;
      }

      // HttpOnly cookie path: the actual JWT is not readable by JS.
      // Trust the auth flag + stored user data for UI state; the HttpOnly
      // cookie authenticates every API call automatically.
      if (!storedToken) {
        // Only hasSession cookie, no JS token - hydrated but not setting auth
        set({ isHydrated: true, isLoading: false });
        return;
      }

      // Legacy path: a JS-readable token exists — validate it server-side.
      // Do NOT set provisional auth yet; wait for validation to complete.
      try {
        const validateStartTime = Date.now();
        const payload = (await apiClient.validateToken(storedToken)) as ValidateTokenResponse;
        const validationDuration = Date.now() - validateStartTime;

        if (payload && payload.valid === false) {
          devWarn('Token validation failed: invalid token');
          get().clearSession();
          set({ isHydrated: true, isLoading: false });
          return;
        }

        const candidateUser = payload && payload.user ? payload.user : null;
        const validatedUser =
          candidateUser && typeof candidateUser === 'object' && 'id' in candidateUser
            ? candidateUser
            : storedUser;

        // Keep provisional auth if the backend response shape is incomplete.
        if (!validatedUser) {
          devWarn('Token validation incomplete: no user in response');
          set({
            token: storedToken,
            user: storedUser,
            isAuthenticated: true,
            isHydrated: true,
            isLoading: false,
          });
          return;
        }

        if (typeof validatedUser !== 'object' || !('id' in validatedUser)) {
          devWarn('Token validation failed: invalid user object');
          set({ isHydrated: true, isLoading: false });
          return;
        }

        // Refresh localStorage + cookies (auth/admin flags used by middleware).
        persistAuthSession({
          token: storedToken,
          user: validatedUser,
          expiresIn: payload?.expires_in,
        });

        set({
          token: storedToken,
          user: validatedUser,
          isAuthenticated: true,
          isHydrated: true,
          isLoading: false,
        });
      } catch (error) {
        const status =
          typeof error === 'object' && error !== null && 'status' in error
            ? Number((error as { status?: unknown }).status)
            : undefined;

        // Log error for debugging
        const errorMessage = error instanceof Error ? error.message : String(error);
        devWarn('Token validation error', {
          status,
          message: errorMessage,
          type: error instanceof Error ? error.constructor.name : typeof error,
        });

        // Hard auth failures invalidate local session.
        if (status === 401 || status === 403) {
          get().clearSession();
          set({ isHydrated: true, isLoading: false });
          return;
        }

        // Network/timeout errors are transient: set provisional auth as fallback
        // to allow UI to work. The HttpOnly cookie will handle auth on API calls.
        const hasValidFallback = Boolean(storedToken) && Boolean(storedUser);
        set({
          token: storedToken,
          user: storedUser,
          isAuthenticated: hasValidFallback,
          isHydrated: true,
          isLoading: false,
        });
      }
    })();

    try {
      await bootstrapPromise;
    } finally {
      bootstrapPromise = null;
    }
  },

  hasRole: (role: string) => {
    const { user } = get();
    if (!user) return false;
    if (typeof user.role !== 'string' && !Array.isArray(user.roles)) {
      return false;
    }
    return user.role === role || Boolean(user.roles?.includes(role));
  },

  hasAnyRole: (roles: string[]) => {
    const { user } = get();
    if (!user || !Array.isArray(roles) || roles.length === 0) return false;
    const userRole = typeof user.role === 'string' ? user.role : '';
    const userRoles = Array.isArray(user.roles) ? user.roles : [];
    return roles.some((role) => role === userRole || userRoles.includes(role));
  },
}));
