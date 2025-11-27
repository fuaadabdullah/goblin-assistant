import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { runtimeClient } from '../api/api-client';

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
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    try {
      setIsLoading(true);

      const { token, user: userData } = await runtimeClient.login(email, password);

      // Store token
      localStorage.setItem('auth_token', token);
      setToken(token);
      setUser(userData);
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

      const { token, user: userData } = await runtimeClient.register(email, password, name);

      // Store token
      localStorage.setItem('auth_token', token);
      setToken(token);
      setUser(userData);
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithGoogle = async (): Promise<void> => {
    try {
      setIsLoading(true);

      // Get Google OAuth URL
      const response = await fetch(
        `${import.meta.env.VITE_FASTAPI_URL || 'http://127.0.0.1:8001'}/auth/google/url`,
        {
          method: 'GET',
        }
      );

      if (!response.ok) {
        throw new Error('Failed to get Google auth URL');
      }

      const data = await response.json();
      const authUrl = data.authorization_url;

      // Redirect to Google OAuth
      window.location.href = authUrl;
    } catch (error) {
      console.error('Google login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const registerPasskey = async (email: string): Promise<void> => {
    try {
      setIsLoading(true);

      // Get challenge from server
      const challengeResponse = await fetch(
        `${import.meta.env.VITE_FASTAPI_URL || 'http://127.0.0.1:8001'}/auth/passkey/challenge`,
        {
          method: 'POST',
        }
      );

      if (!challengeResponse.ok) {
        throw new Error('Failed to get challenge');
      }

      const { challenge } = await challengeResponse.json();

      // Create credential creation options
      const publicKeyCredentialCreationOptions: PublicKeyCredentialCreationOptions = {
        challenge: Uint8Array.from(atob(challenge.replace(/-/g, '+').replace(/_/g, '/')), c =>
          c.charCodeAt(0)
        ),
        rp: {
          name: 'Goblin Assistant',
          id: window.location.hostname,
        },
        user: {
          id: Uint8Array.from(email, c => c.charCodeAt(0)),
          name: email,
          displayName: email,
        },
        pubKeyCredParams: [
          { alg: -7, type: 'public-key' }, // ES256
          { alg: -257, type: 'public-key' }, // RS256
        ],
        authenticatorSelection: {
          authenticatorAttachment: 'platform',
          userVerification: 'preferred',
        },
        timeout: 60000,
        attestation: 'direct',
      };

      // Create credential
      const credential = (await navigator.credentials.create({
        publicKey: publicKeyCredentialCreationOptions,
      })) as PublicKeyCredential;

      if (credential) {
        // Extract public key and register with server
        const publicKey = (credential.response as AuthenticatorAttestationResponse).getPublicKey();
        if (!publicKey) {
          throw new Error('Failed to get public key from credential');
        }

        const response = await fetch(
          `${import.meta.env.VITE_FASTAPI_URL || 'http://127.0.0.1:8001'}/auth/passkey/register`,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: email,
              credential_id: btoa(String.fromCharCode(...new Uint8Array(credential.rawId))),
              public_key: btoa(String.fromCharCode(...new Uint8Array(publicKey))),
            }),
          }
        );

        if (!response.ok) {
          throw new Error('Passkey registration failed');
        }

        // Passkey registered successfully
        return;
      }

      throw new Error('Failed to create passkey credential');
    } catch (error) {
      console.error('Passkey registration error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setToken(null);
    setUser(null);
  };

  const checkAuth = async (): Promise<void> => {
    try {
      const storedToken = localStorage.getItem('auth_token');

      if (!storedToken) {
        setIsLoading(false);
        return;
      }

      setToken(storedToken);

      // Validate token with backend
      const response = await fetch(
        `${import.meta.env.VITE_FASTAPI_URL || 'http://127.0.0.1:8001'}/auth/me`,
        {
          method: 'GET',
          headers: {
            Authorization: `Bearer ${storedToken}`,
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
  };

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
