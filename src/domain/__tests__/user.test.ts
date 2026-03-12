import type { DomainUser } from '../user';

describe('domain/user types', () => {
  it('should build a DomainUser with required fields', () => {
    const user: DomainUser = { id: 'u1' };
    expect(user.id).toBe('u1');
    expect(user.email).toBeUndefined();
    expect(user.role).toBeUndefined();
    expect(user.roles).toBeUndefined();
  });

  it('should build a DomainUser with all fields', () => {
    const user: DomainUser = {
      id: 'u2',
      email: 'test@example.com',
      role: 'admin',
      roles: ['admin', 'user'],
    };
    expect(user.email).toBe('test@example.com');
    expect(user.roles).toContain('admin');
    expect(user.roles).toHaveLength(2);
  });
});
