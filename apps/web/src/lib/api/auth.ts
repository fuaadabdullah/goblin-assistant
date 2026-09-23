import type {
  AuthenticationResponseJSON,
  RegistrationResponseJSON,
} from '@simplewebauthn/browser';

import {
  AUTH_REQUEST_TIMEOUT_MS,
  getCsrfToken,
  getFrontend,
  postFrontend,
  withAuth,
} from './shared';
import type { PasskeyAuthResponse, ValidateTokenResponse } from '../../types/api';
import { getAuthTokenForRequest } from '../../utils/auth-session';

export const authMethods = {
  async passkeyChallenge(email: string) {
    return postFrontend('/api/auth/passkey/challenge', { email });
  },

  async passkeyRegister(email: string, credential: RegistrationResponseJSON) {
    return postFrontend('/api/auth/passkey/register', { email, credential });
  },

  async passkeyAuth(email: string, assertion: AuthenticationResponseJSON) {
    return postFrontend<PasskeyAuthResponse>('/api/auth/passkey/auth', {
      email,
      assertion,
    });
  },

  async register(email: string, password: string, turnstileToken?: string | null) {
    const csrfToken = await getCsrfToken();
    return postFrontend(
      '/api/auth/register',
      { email, password, turnstileToken, csrf_token: csrfToken },
      { timeout: AUTH_REQUEST_TIMEOUT_MS }
    );
  },

  async login(email: string, password: string) {
    const csrfToken = await getCsrfToken();
    return postFrontend(
      '/api/auth/login',
      { email, password, csrf_token: csrfToken },
      { timeout: AUTH_REQUEST_TIMEOUT_MS }
    );
  },

  async validateToken(token?: string): Promise<ValidateTokenResponse> {
    const resolvedToken = token?.trim() || (await getAuthTokenForRequest());
    return postFrontend<ValidateTokenResponse>(
      '/api/auth/validate',
      { token: resolvedToken ?? '' },
      {
        headers: resolvedToken
          ? {
              Authorization: `Bearer ${resolvedToken}`,
              'Content-Type': 'application/json',
            }
          : {
              'Content-Type': 'application/json',
            },
      }
    );
  },

  async logout() {
    return postFrontend('/api/auth/logout', undefined, withAuth());
  },

  async getGoogleAuthUrl() {
    const payload = await getFrontend<{ url?: string; authorization_url?: string }>(
      '/api/auth/google/url',
      {
        timeout: AUTH_REQUEST_TIMEOUT_MS,
      }
    );

    const url = payload?.url || payload?.authorization_url;
    if (!url) {
      throw new Error('Google sign-in URL is unavailable.');
    }
    return { url };
  },
};
