import type { DomainUser } from '../user';

describe('DomainUser type', () => {
  it('creates a user with just an id', () => {
    const user: DomainUser = { id: 'user1' };
    expect(user.id).toBe('user1');
  });

  it('creates a user with email', () => {
    const user: DomainUser = { id: 'user1', email: 'test@example.com' };
    expect(user.email).toBe('test@example.com');
  });

  it('creates a user with a single role', () => {
    const user: DomainUser = { id: 'user1', role: 'admin' };
    expect(user.role).toBe('admin');
  });

  it('creates a user with multiple roles', () => {
    const user: DomainUser = { id: 'user1', roles: ['admin', 'user'] };
    expect(user.roles).toEqual(['admin', 'user']);
  });

  it('creates a fully populated user', () => {
    const user: DomainUser = {
      id: 'user1',
      email: 'test@example.com',
      role: 'admin',
      roles: ['admin', 'moderator'],
    };
    expect(user.id).toBe('user1');
    expect(user.email).toBe('test@example.com');
    expect(user.role).toBe('admin');
    expect(user.roles).toHaveLength(2);
  });
});
