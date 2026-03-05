import { isAdminUser, type AccessUser } from '../access';

describe('Access Control Utilities', () => {
  describe('isAdminUser', () => {
    it('should return true for admin user', () => {
      const adminUser: AccessUser = {
        id: '1',
        email: 'admin@example.com',
        role: 'admin',
      };

      expect(isAdminUser(adminUser)).toBe(true);
    });

    it('should return false for non-admin user', () => {
      const regularUser: AccessUser = {
        id: '2',
        email: 'user@example.com',
        role: 'user',
      };

      expect(isAdminUser(regularUser)).toBe(false);
    });

    it('should return false when user is undefined', () => {
      expect(isAdminUser(undefined)).toBe(false);
    });

    it('should return false when user is null', () => {
      expect(isAdminUser(null)).toBe(false);
    });

    it('should return false for user without role', () => {
      const userWithoutRole: Partial<AccessUser> = {
        id: '3',
        email: 'test@example.com',
      };

      expect(isAdminUser(userWithoutRole as AccessUser)).toBe(false);
    });
  });
});
