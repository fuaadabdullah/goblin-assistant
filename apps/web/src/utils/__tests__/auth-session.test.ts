import { persistAuthSession, clearAuthSession, getAuthToken, isAuthenticated } from '../auth-session';

jest.mock('../access', () => ({
  isAdminUser: jest.fn(() => false),
}));

describe('Auth Session Utilities', () => {
  beforeEach(() => {
    localStorage.clear();
    // Clear all cookies
    document.cookie.split(';').forEach(c => {
      const name = c.trim().split('=')[0];
      if (name) document.cookie = `${name}=; Path=/; Max-Age=0`;
    });
  });

  describe('persistAuthSession', () => {
    it('should NOT write session_token cookie (HttpOnly set by backend)', () => {
      persistAuthSession({
        token: 'jwt.token.here',
        user: { id: '123', email: 'test@example.com', name: 'Test User' } as any,
        expiresIn: 3600,
      });

      expect(document.cookie).not.toContain('session_token=');
    });

    it('should persist user data in localStorage', () => {
      persistAuthSession({
        token: 'jwt.token.here',
        user: { id: '123', email: 'test@example.com', name: 'Test User' } as any,
        expiresIn: 3600,
      });

      const stored = localStorage.getItem('user_data');
      expect(stored).toBeDefined();
      expect(JSON.parse(stored!)).toEqual(
        expect.objectContaining({ id: '123', email: 'test@example.com' }),
      );
    });

    it('should set goblin_auth flag cookie', () => {
      persistAuthSession({
        token: 'jwt.token.here',
        user: { id: '123', email: 'test@example.com', name: 'Test User' } as any,
      });

      expect(document.cookie).toContain('goblin_auth=');
    });

    it('should NOT write refresh_token cookie (HttpOnly set by backend)', () => {
      persistAuthSession({
        token: 'jwt.token.here',
        refreshToken: 'refresh.token.here',
        user: { id: '123', email: 'test@example.com', name: 'Test User' } as any,
      });

      expect(document.cookie).not.toContain('refresh_token=');
    });
  });

  describe('isAuthenticated', () => {
    it('should return true when goblin_auth flag is set', () => {
      document.cookie = 'goblin_auth=1; Path=/';
      expect(isAuthenticated()).toBe(true);
    });

    it('should return false when no session exists', () => {
      expect(isAuthenticated()).toBe(false);
    });

    it('should fall back to legacy localStorage auth_token', () => {
      localStorage.setItem('auth_token', 'legacy-token');
      expect(isAuthenticated()).toBe(true);
    });
  });

  describe('getAuthToken', () => {
    it('should retrieve token from cookie', () => {
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
