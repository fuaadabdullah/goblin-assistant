import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { runtimeClient } from '../lib/api/api-client';

interface User {
  id: string;
  email: string;
  name?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  registerPasskey: (email: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = () => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
  };

  const checkAuth = useCallback(async (): Promise<void> => {
    try {
      const storedToken = localStorage.getItem('auth_token');

      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      setToken(storedToken);

      // Validate token with backend
      const response = await fetch(
        `${import.meta.env.VITE_FASTAPI_URL || 'http://127.0.0.1:8001'}/auth/validate`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${storedToken}`,
            'Content-Type': 'application/json',
          },
        }
      );

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        // Token is invalid, clear auth data
        logout();
      }
    } catch (error) {
      console.error('Auth check error:', error);
      logout();
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Check for stored token on app start
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    const storedUserData = localStorage.getItem('user_data');

    if (storedToken) {
      setToken(storedToken);
      if (storedUserData) {
        try {
          const userData = JSON.parse(storedUserData);
          setUser(userData);
        } catch (error) {
          console.error('Error parsing stored user data:', error);
          localStorage.removeItem('user_data');
        }
      }
      // Validate token with backend
      checkAuth();
    } else {
      setIsLoading(false);
    }
  }, [checkAuth]);

  const value: AuthContextType = {
    user,
    token,
    isLoading,
    isAuthenticated: !!token && !!user,
    login,
    register,
    loginWithGoogle,
    registerPasskey,
    logout,
    checkAuth,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
