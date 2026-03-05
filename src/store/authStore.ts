import { create } from 'zustand';
import type { User } from '../types/api';
import { clearAuthSession, getAuthToken, persistAuthSession } from '../utils/auth-session';

type SessionInput = {
  token: string;
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
  } catch {
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

  setSession: ({ token, user, expiresIn }: SessionInput) => {
    persistAuthSession({ token, user, expiresIn });
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
      const storedUserDataRaw = window.localStorage.getItem('user_data');
      const storedUser = safeJsonParse(storedUserDataRaw) as User | null;

      if (storedToken) {
        set({
          token: storedToken,
          user: storedUser,
          // Cookie-first auth bootstrap keeps the session provisional while
          // backend validation runs, preventing transient boot-time logouts.
          isAuthenticated: true,
        });
      }

      if (!storedToken) {
        set({ isHydrated: true, isLoading: false });
        return;
      }

      try {
        const response = await fetch('/api/auth/validate', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${storedToken}`,
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          // Hard auth failures invalidate the local session.
          if (response.status === 401 || response.status === 403) {
            get().clearSession();
            set({ isHydrated: true, isLoading: false });
            return;
          }
          // Transient failures keep the provisional session.
          set({ isHydrated: true, isLoading: false });
          return;
        }

        const payload = (await response.json()) as any;
        if (payload && payload.valid === false) {
          get().clearSession();
          set({ isHydrated: true, isLoading: false });
          return;
        }

        const candidateUser = (payload && (payload.user || payload)) as User | null;
        const validatedUser =
          candidateUser && typeof candidateUser === 'object' && 'id' in candidateUser
            ? candidateUser
            : storedUser;

        // Keep provisional auth if the backend response shape is incomplete.
        if (!validatedUser) {
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
        // Network/timeouts are treated as transient: keep provisional auth.
        set({ isHydrated: true, isLoading: false });
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
    return user.role === role || Boolean(user.roles?.includes(role));
  },

  hasAnyRole: (roles: string[]) => {
    const { user } = get();
    if (!user) return false;
    return roles.some(role => user.role === role || Boolean(user.roles?.includes(role)));
  },
}));
