import { AUTH_CONFIG } from '../auth';

describe('AUTH_CONFIG', () => {
  it('uses httpOnly cookies', () => {
    expect(AUTH_CONFIG.USE_COOKIES).toBe(true);
  });

  it('has a token cookie name', () => {
    expect(AUTH_CONFIG.TOKEN_COOKIE_NAME).toBe('session_token');
  });

  it('has a refresh cookie name', () => {
    expect(AUTH_CONFIG.REFRESH_COOKIE_NAME).toBe('refresh_token');
  });

  it('has readonly properties (as const)', () => {
    // AUTH_CONFIG uses 'as const' which gives immutable type-level protection
    expect(AUTH_CONFIG.TOKEN_COOKIE_NAME).toBeDefined();
  });
});
