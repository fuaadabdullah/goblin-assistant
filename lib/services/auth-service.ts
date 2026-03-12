'use client';

import { apiClient } from '@/lib/api';
import { clearAuthSession, getAuthToken, persistAuthSession } from '@/utils/auth-session';

type LoginApiResponse = {
  access_token?: string;
  refresh_token?: string;
  expires_in?: number;
  user?: { id?: string; email?: string };
};

const mapUser = (user?: { id?: string; email?: string }, fallbackEmail = '') => ({
  id: user?.id ?? '',
  email: user?.email ?? fallbackEmail,
  name: (user?.email ?? fallbackEmail).split('@')[0] ?? '',
});

export const authService = {
  signIn: async (email: string, password: string) => {
    const response = (await apiClient.login(email, password)) as LoginApiResponse;
    const token = response?.access_token ?? '';
    const expiresIn = response?.expires_in;
    persistAuthSession({ token, refreshToken: response?.refresh_token, user: response?.user, expiresIn });
    return {
      user: mapUser(response?.user, email),
      session: {
        token,
        expiresAt: new Date(Date.now() + (expiresIn ?? 3600) * 1000).toISOString(),
      },
    };
  },

  signUp: async (email: string, password: string, _name?: string) => {
    const response = (await apiClient.register(email, password)) as LoginApiResponse;
    const token = response?.access_token ?? '';
    const expiresIn = response?.expires_in;
    persistAuthSession({ token, refreshToken: response?.refresh_token, user: response?.user, expiresIn });
    return {
      user: mapUser(response?.user, email),
      session: {
        token,
        expiresAt: new Date(Date.now() + (expiresIn ?? 3600) * 1000).toISOString(),
      },
    };
  },

  signOut: async () => {
    try {
      await apiClient.logout();
    } finally {
      clearAuthSession();
    }
    return { success: true };
  },

  validateToken: async (token: string) => {
    const response = await apiClient.validateToken(token);
    return mapUser(response?.user);
  },

  getCurrentUser: async () => {
    const token = getAuthToken();
    if (!token) return { id: '', email: '', name: '' };
    const response = await apiClient.validateToken(token);
    return mapUser(response?.user);
  },
};
