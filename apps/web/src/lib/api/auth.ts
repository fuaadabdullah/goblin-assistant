import {
  AUTH_REQUEST_TIMEOUT_MS,
  PasskeyCredential,
  getCsrfToken,
  postFrontend,
  withAuth,
  getFrontend,
} from './shared';
import type { ValidateTokenResponse } from '../../types/api';

export const authMethods = {
  async passkeyChallenge(email: string) {
    return postFrontend('/api/auth/passkey/challenge', { email });
  },

  async passkeyRegister(email: string, credential: PasskeyCredential) {
    return postFrontend('/api/auth/passkey/register', { email, credential });
  },

  async passkeyAuth(email: string, assertion: PasskeyCredential) {
    return postFrontend('/api/auth/passkey/auth', { email, assertion });
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

  async validateToken(token: string): Promise<ValidateTokenResponse> {
    return postFrontend<ValidateTokenResponse>(
      '/api/auth/validate',
      {},
      {
        headers: {
          Authorization: `Bearer ${token}`,
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
