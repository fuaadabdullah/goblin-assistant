import { renderHook, act } from '@testing-library/react';
import { useAuthStore } from '../authStore';

describe('Auth Store (Zustand)', () => {
  beforeEach(() => {
    const { result } = renderHook(() => useAuthStore());
    act(() => {
      result.current.logout();
    });
  });

  it('should have initial state', () => {
    const { result } = renderHook(() => useAuthStore());
    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should set user and token on login', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.login({
        user: { id: '123', email: 'test@example.com', name: 'Test' },
        token: 'jwt.token',
      });
    });

    expect(result.current.user).toEqual({
      id: '123',
      email: 'test@example.com',
      name: 'Test',
    });
    expect(result.current.token).toBe('jwt.token');
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('should clear user and token on logout', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.login({
        user: { id: '123', email: 'test@example.com', name: 'Test' },
        token: 'jwt.token',
      });
    });

    act(() => {
      result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('should set user', () => {
    const { result } = renderHook(() => useAuthStore());
    const newUser = { id: '456', email: 'new@example.com', name: 'New User' };

    act(() => {
      result.current.setUser(newUser);
    });

    expect(result.current.user).toEqual(newUser);
  });

  it('should set token', () => {
    const { result } = renderHook(() => useAuthStore());
    const newToken = 'new.jwt.token';

    act(() => {
      result.current.setToken(newToken);
    });

    expect(result.current.token).toBe(newToken);
  });

  it('should handle error state', () => {
    const { result } = renderHook(() => useAuthStore());
    const error = 'Authentication failed';

    act(() => {
      result.current.setError(error);
    });

    expect(result.current.error).toBe(error);
  });

  it('should clear error state', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.setError('Some error');
      result.current.clearError();
    });

    expect(result.current.error).toBeNull();
  });
});
