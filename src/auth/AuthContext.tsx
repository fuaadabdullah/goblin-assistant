import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';

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

  const login = async (email: string, password: string): Promise<void> => {
    try {
      setIsLoading(true);
      const response = await fetch(
        `${import.meta.env.VITE_FASTAPI_URL || 'http://127.0.0.1:8001'}/auth/login`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, password }),
        }
      );

      if (response.ok) {
        const data = await response.json();
        // Backend may return either `token` or `access_token` depending on implementation
        const tokenValue = (data && (data.token || data.access_token)) || null;
        const userData = (data && (data.user || data.userData)) || null;

        if (!tokenValue || !userData) {
          console.error('Login: unexpected response shape', data);
          throw new Error('Login failed - invalid server response');
        }

        localStorage.setItem('auth_token', tokenValue);
        localStorage.setItem('user_data', JSON.stringify(userData));
        setToken(tokenValue);
        setUser(userData);
      } else {
        // Attempt to extract server message for better error propagation
        let errMsg = 'Login failed';
        try {
          const errJson = await response.json();
          errMsg = errJson.error || errJson.message || errMsg;
        } catch (e) {
          // ignore parsing error
        }
        throw new Error(errMsg);
      }
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, name?: string): Promise<void> => {
    try {
      setIsLoading(true);
      const response = await fetch(
        `${import.meta.env.VITE_FASTAPI_URL || 'http://127.0.0.1:8001'}/auth/register`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ email, password, name }),
        }
      );

      if (response.ok) {
        const data = await response.json();
        const { token, user: userData } = data;

        localStorage.setItem('auth_token', token);
        localStorage.setItem('user_data', JSON.stringify(userData));
        setToken(token);
        setUser(userData);
      } else {
        // Attempt to extract server message for better error propagation
        let errMsg = 'Registration failed';
        try {
          const errJson = await response.json();
          errMsg = errJson.error || errJson.message || errMsg;
        } catch (e) {
          // ignore parsing error
        }
        throw new Error(errMsg);
      }
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithGoogle = async (): Promise<void> => {
    // TODO: Implement Google OAuth login
    throw new Error('Google login not implemented yet');
  };

  const registerPasskey = async (_email: string): Promise<void> => {
    // TODO: Implement passkey registration
    throw new Error('Passkey registration not implemented yet');
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
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
        const payload = await response.json();
        // Handle common response shapes
        if (payload && payload.valid === false) {
          // Invalid token
          logout();
          return;
        }

        const validatedUser = payload && (payload.user || payload);
        // If we received a wrapper without user, we expect a user object; otherwise treat as invalid
        if (!validatedUser || !validatedUser.id) {
          console.error('Auth validate: unexpected response', payload);
          logout();
          return;
        }

        setUser(validatedUser as any);
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
