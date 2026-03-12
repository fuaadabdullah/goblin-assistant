import { renderHook, act } from '@testing-library/react';
import { useAuthStore } from '../authStore';

jest.mock('@/api', () => ({
  apiClient: { validateToken: jest.fn() },
}));

jest.mock('@/utils/auth-session', () => ({
  persistAuthSession: jest.fn(),
  clearAuthSession: jest.fn(),
  getAuthToken: jest.fn(() => null),
}));

describe('Auth Store (Zustand)', () => {
  beforeEach(() => {
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.clearSession();
    });
  });

  it('should have initial unauthenticated state', () => {
    const { result } = renderHook(() => useAuthStore());
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should set session with user and token', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.setSession({
        token: 'jwt.token',
        user: { id: '123', email: 'test@example.com', name: 'Test', role: 'user' } as any,
      });
    });

    expect(result.current.token).toBe('jwt.token');
    expect(result.current.user).toEqual(
      expect.objectContaining({ id: '123', email: 'test@example.com' }),
    );
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should clear session', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.setSession({
        token: 'jwt.token',
        user: { id: '123', email: 'test@example.com', name: 'Test', role: 'user' } as any,
      });
    });

    act(() => {
      result.current.clearSession();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('hasRole returns true for matching role', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.setSession({
        token: 'jwt.token',
        user: { id: '1', email: 'a@b.com', name: 'A', role: 'admin' } as any,
      });
    });

    expect(result.current.hasRole('admin')).toBe(true);
    expect(result.current.hasRole('user')).toBe(false);
  });

  it('hasAnyRole returns true if any role matches', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.setSession({
        token: 'jwt.token',
        user: { id: '1', email: 'a@b.com', name: 'A', role: 'editor' } as any,
      });
    });

    expect(result.current.hasAnyRole(['admin', 'editor'])).toBe(true);
    expect(result.current.hasAnyRole(['admin', 'superuser'])).toBe(false);
  });

  it('hasRole returns false when no user', () => {
    const { result } = renderHook(() => useAuthStore());
    expect(result.current.hasRole('admin')).toBe(false);
  });
});
