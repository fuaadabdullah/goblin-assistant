import { isAdminUser } from '../access';

describe('isAdminUser', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
    delete process.env.NEXT_PUBLIC_ADMIN_EMAILS;
    delete process.env.NEXT_PUBLIC_ADMIN_DOMAINS;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it('returns false for null user', () => {
    expect(isAdminUser(null)).toBe(false);
  });

  it('returns false for undefined user', () => {
    expect(isAdminUser(undefined)).toBe(false);
  });

  it('returns true when user role is admin', () => {
    expect(isAdminUser({ role: 'admin' })).toBe(true);
  });

  it('returns true when user role is owner', () => {
    expect(isAdminUser({ role: 'owner' })).toBe(true);
  });

  it('returns true when user role is superuser', () => {
    expect(isAdminUser({ role: 'superuser' })).toBe(true);
  });

  it('returns false for non-admin role', () => {
    expect(isAdminUser({ role: 'user' })).toBe(false);
  });

  it('returns true when user has admin in roles array', () => {
    expect(isAdminUser({ roles: ['admin', 'user'] })).toBe(true);
  });

  it('returns true when user has owner in roles array', () => {
    expect(isAdminUser({ roles: ['owner'] })).toBe(true);
  });

  it('returns false when roles array has no admin role', () => {
    expect(isAdminUser({ roles: ['user', 'moderator'] })).toBe(false);
  });

  it('returns false for user with no role info', () => {
    expect(isAdminUser({ email: 'test@example.com' })).toBe(false);
  });
});