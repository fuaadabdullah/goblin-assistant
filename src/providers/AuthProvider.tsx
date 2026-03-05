// providers/AuthProvider.tsx
'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { apiClient } from '../../lib/services';
import type { User, AuthState, LoginCredentials, RegisterData } from '../../lib/types';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  sessionToken?: string;
  refreshToken?: string;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  refreshTokenFn: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isLoading: true,
    isAuthenticated: false,
  });

  // Check for existing session on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('auth-token');
      if (!token) {
        setAuthState(prev => ({ ...prev, isLoading: false }));
        return;
      }

      try {
        // Validate token with backend
        const response = await apiClient.get<User>('/auth/me');
        if (response.success && response.data) {
          setAuthState({
            user: response.data,
            isLoading: false,
            isAuthenticated: true,
            sessionToken: token,
          });
          apiClient.setAuthToken(token);
        } else {
          // Token invalid, clear it
          localStorage.removeItem('auth-token');
          setAuthState(prev => ({ ...prev, isLoading: false }));
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        localStorage.removeItem('auth-token');
        setAuthState(prev => ({ ...prev, isLoading: false }));
      }
    };

    checkAuth();
  }, []);

  const login = async (credentials: LoginCredentials) => {
    setAuthState(prev => ({ ...prev, isLoading: true }));

    try {
      const response = await apiClient.post<{
        user: User;
        token: string;
        refreshToken: string;
      }>('/auth/login', credentials);

      if (!response.success || !response.data) {
        throw new Error(response.error?.message || 'Login failed');
      }

      const { user, token, refreshToken } = response.data;

      localStorage.setItem('auth-token', token);
      localStorage.setItem('refresh-token', refreshToken);

      apiClient.setAuthToken(token);

      setAuthState({
        user,
        isLoading: false,
        isAuthenticated: true,
        sessionToken: token,
        refreshToken,
      });
    } catch (error) {
      setAuthState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  };

  const register = async (data: RegisterData) => {
    setAuthState(prev => ({ ...prev, isLoading: true }));

    try {
      const response = await apiClient.post<{
        user: User;
        token: string;
        refreshToken: string;
      }>('/auth/register', data);

      if (!response.success || !response.data) {
        throw new Error(response.error?.message || 'Registration failed');
      }

      const { user, token, refreshToken } = response.data;

      localStorage.setItem('auth-token', token);
      localStorage.setItem('refresh-token', refreshToken);

      apiClient.setAuthToken(token);

      setAuthState({
        user,
        isLoading: false,
        isAuthenticated: true,
        sessionToken: token,
        refreshToken,
      });
    } catch (error) {
      setAuthState(prev => ({ ...prev, isLoading: false }));
      throw error;
    }
  };

  const logout = async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch (error) {
      console.error('Logout API call failed:', error);
    }

    // Clear local state regardless of API call result
    localStorage.removeItem('auth-token');
    localStorage.removeItem('refresh-token');
    apiClient.clearAuthToken();

    setAuthState({
      user: null,
      isLoading: false,
      isAuthenticated: false,
    });
  };

  const refreshToken = async () => {
    const refreshToken = localStorage.getItem('refresh-token');
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await apiClient.post<{
        token: string;
        refreshToken: string;
      }>('/auth/refresh', { refreshToken });

      if (!response.success || !response.data) {
        throw new Error(response.error?.message || 'Token refresh failed');
      }

      const { token: newToken, refreshToken: newRefreshToken } = response.data;

      localStorage.setItem('auth-token', newToken);
      localStorage.setItem('refresh-token', newRefreshToken);
      apiClient.setAuthToken(newToken);

      setAuthState(prev => ({
        ...prev,
        sessionToken: newToken,
        refreshToken: newRefreshToken,
      }));
    } catch (error) {
      // Refresh failed, logout user
      await logout();
      throw error;
    }
  };

  return (
    <AuthContext.Provider value={{
      ...authState,
      login,
      register,
      logout,
      refreshTokenFn: refreshToken,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
