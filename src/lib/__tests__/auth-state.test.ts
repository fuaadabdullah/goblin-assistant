import { hasRole, hasAnyRole } from '../auth-state';

describe('hasRole', () => {
  it('returns false for null user', () => {
    expect(hasRole(null, 'admin')).toBe(false);
  });

  it('returns false for undefined user', () => {
    expect(hasRole(undefined, 'admin')).toBe(false);
  });

  it('returns true when user has matching role string', () => {
    const user = { id: '1', role: 'admin', roles: ['admin', 'user'] };
    expect(hasRole(user, 'admin')).toBe(true);
  });

  it('returns false when user has different role string', () => {
    const user = { id: '1', role: 'user' };
    expect(hasRole(user, 'admin')).toBe(false);
  });

  it('returns true when user has role in roles array', () => {
    const user = { id: '1', roles: ['admin', 'moderator'] };
    expect(hasRole(user, 'moderator')).toBe(true);
  });

  it('returns false when role not in roles array', () => {
    const user = { id: '1', roles: ['user', 'moderator'] };
    expect(hasRole(user, 'admin')).toBe(false);
  });
});

describe('hasAnyRole', () => {
  it('returns false for null user', () => {
    expect(hasAnyRole(null, ['admin'])).toBe(false);
  });

  it('returns false for empty roles array', () => {
    const user = { id: '1', role: 'admin' };
    expect(hasAnyRole(user, [])).toBe(false);
  });

  it('returns true when user has at least one role', () => {
    const user = { id: '1', role: 'admin', roles: ['admin'] };
    expect(hasAnyRole(user, ['user', 'admin'])).toBe(true);
  });

  it('returns false when user has none of the roles', () => {
    const user = { id: '1', role: 'user' };
    expect(hasAnyRole(user, ['admin', 'moderator'])).toBe(false);
  });
});