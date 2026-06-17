import { persistAuthSession, clearAuthSession, getAuthToken } from '../auth-session';

describe('Auth Session Utilities', () => {
  beforeEach(() => {
    localStorage.clear();
    document.cookie.split(';').forEach((c) => {
      const name = c.trim().split('=')[0];
      if (name) document.cookie = `${name}=; Path=/; Max-Age=0`;
    });
  });

  describe('persistAuthSession', () => {
    it('should persist user data in localStorage', () => {
      persistAuthSession({
        user: { id: '123', email: 'test@example.com', name: 'Test User' } as any,
      });

      const stored = localStorage.getItem('user_data');
      expect(stored).toBeDefined();
      expect(JSON.parse(stored!)).toEqual(
        expect.objectContaining({ id: '123', email: 'test@example.com' })
      );
    });

    it('should not write goblin_auth or goblin_admin cookies', () => {
      persistAuthSession({
        token: 'jwt.token.here',
        user: { id: '123', email: 'test@example.com', name: 'Test User' } as any,
      });

      expect(document.cookie).not.toContain('goblin_auth=');
      expect(document.cookie).not.toContain('goblin_admin=');
    });

    it('should not write session_token or refresh_token cookies', () => {
      persistAuthSession({
        token: 'jwt.token.here',
        refreshToken: 'refresh.token.here',
        user: { id: '123', email: 'test@example.com', name: 'Test User' } as any,
      });

      expect(document.cookie).not.toContain('session_token=');
      expect(document.cookie).not.toContain('refresh_token=');
    });
  });

  describe('getAuthToken', () => {
    it('should retrieve token from session_token cookie', () => {
      document.cookie = 'session_token=my-jwt-token; Path=/';
      expect(getAuthToken()).toBe('my-jwt-token');
    });

    it('should fall back to localStorage auth_token', () => {
      localStorage.setItem('auth_token', 'legacy-token');
      expect(getAuthToken()).toBe('legacy-token');
    });

    it('should return null when no token exists', () => {
      expect(getAuthToken()).toBeNull();
    });
  });

  describe('clearAuthSession', () => {
    it('should clear localStorage items', () => {
      localStorage.setItem('auth_token', 'token');
      localStorage.setItem('user_data', JSON.stringify({ id: '123' }));

      clearAuthSession();

      expect(localStorage.getItem('auth_token')).toBeNull();
      expect(localStorage.getItem('user_data')).toBeNull();
    });

    it('should handle clearing when no session exists', () => {
      expect(() => clearAuthSession()).not.toThrow();
    });
  });
});
