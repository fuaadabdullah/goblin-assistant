'use client';

export const authService = {
  signIn: async (email: string, _password: string) => {
    console.log('AuthService.signIn called with:', email);
    // Mock implementation
    return {
      user: {
        id: 'mock-user-id',
        email,
        name: 'Mock User',
      },
      session: {
        token: 'mock-session-token',
        expiresAt: new Date(Date.now() + 3600000).toISOString(),
      },
    };
  },

  signUp: async (email: string, password: string, name?: string) => {
    console.log('AuthService.signUp called with:', email, name);
    // Mock implementation
    return {
      user: {
        id: 'mock-user-id',
        email,
        name: name || 'New User',
      },
      session: {
        token: 'mock-session-token',
        expiresAt: new Date(Date.now() + 3600000).toISOString(),
      },
    };
  },

  signOut: async () => {
    console.log('AuthService.signOut called');
    // Mock implementation
    return { success: true };
  },

  validateToken: async (token: string) => {
    console.log('AuthService.validateToken called with:', token);
    // Mock implementation
    return {
      id: 'mock-user-id',
      email: 'user@example.com',
      name: 'Mock User',
    };
  },

  getCurrentUser: async () => {
    console.log('AuthService.getCurrentUser called');
    // Mock implementation
    return {
      id: 'mock-user-id',
      email: 'user@example.com',
      name: 'Mock User',
    };
  },
};
