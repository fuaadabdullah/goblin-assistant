import { persistAuthSession, clearAuthSession } from '../auth-session';

describe('Auth Session Utilities', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('persistAuthSession', () => {
    it('should persist auth token to session storage', () => {
      const token = 'jwt.token.here';
      const user = { id: '123', email: 'test@example.com', name: 'Test User' };

      persistAuthSession({ token, user, expiresIn: 3600 });

      const stored = sessionStorage.getItem('goblin_auth_token');
      expect(stored).toBe(token);
    });

    it('should persist user info to session storage', () => {
      const token = 'jwt.token.here';
      const user = { id: '123', email: 'test@example.com', name: 'Test User' };

      persistAuthSession({ token, user, expiresIn: 3600 });

      const storedUser = sessionStorage.getItem('goblin_auth_user');
      expect(storedUser).toBeDefined();
      expect(JSON.parse(storedUser!)).toEqual(user);
    });

    it('should persist expiration time', () => {
      const token = 'jwt.token.here';
      const user = { id: '123', email: 'test@example.com', name: 'Test User' };

      persistAuthSession({ token, user, expiresIn: 3600 });

      const expiresAt = sessionStorage.getItem('goblin_auth_expires_at');
      expect(expiresAt).toBeDefined();
      expect(Number(expiresAt)).toBeGreaterThan(Date.now());
    });
  });

  describe('clearAuthSession', () => {
    it('should clear all auth data from storage', () => {
      sessionStorage.setItem('goblin_auth_token', 'token');
      sessionStorage.setItem('goblin_auth_user', JSON.stringify({ id: '123' }));
      sessionStorage.setItem(
        'goblin_auth_expires_at',
        String(Date.now() + 3600000),
      );

      clearAuthSession();

      expect(sessionStorage.getItem('goblin_auth_token')).toBeNull();
      expect(sessionStorage.getItem('goblin_auth_user')).toBeNull();
      expect(sessionStorage.getItem('goblin_auth_expires_at')).toBeNull();
    });

    it('should handle clearing when no session exists', () => {
      expect(() => clearAuthSession()).not.toThrow();
    });
  });
});
