// app/lib/services/mock-auth-service.ts
// Mock authentication service for development when Supabase is not configured

export interface User {
  id: string;
  email: string;
  name?: string;
  created_at: string;
}

export interface AuthData {
  user: User | null;
  session: {
    access_token: string;
    refresh_token: string;
    expires_at: number;
  } | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  expires_at: number;
}

class MockAuthService {
  private users: Map<string, User> = new Map();
  private sessions: Map<string, AuthData> = new Map();
  private currentUserId: string = 'user-1';

  constructor() {
    // Initialize with multiple default users for testing
    this.users.set('test@example.com', {
      id: 'user-1',
      email: 'test@example.com',
      name: 'Test User',
      created_at: new Date().toISOString(),
    });

    this.users.set('user@example.com', {
      id: 'user-2',
      email: 'user@example.com',
      name: 'Regular User',
      created_at: new Date().toISOString(),
    });

    this.users.set('admin@example.com', {
      id: 'user-3',
      email: 'admin@example.com',
      name: 'Admin User',
      created_at: new Date().toISOString(),
    });

    this.users.set('demo@example.com', {
      id: 'user-4',
      email: 'demo@example.com',
      name: 'Demo User',
      created_at: new Date().toISOString(),
    });
  }

  // Generate a mock JWT token
  private generateToken(userId: string): string {
    const payload = {
      sub: userId,
      email: this.users.get(userId)?.email,
      exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60), // 24 hours
    };
    
    // Simple base64 encoding for mock token
    const header = btoa(JSON.stringify({ alg: 'none', typ: 'JWT' }));
    const encodedPayload = btoa(JSON.stringify(payload));
    return `${header}.${encodedPayload}.`;
  }

  // Sign up a new user
  async signUp(email: string, password: string, name?: string): Promise<AuthData> {
    // Check if user already exists
    if (this.users.has(email)) {
      throw new Error('User already exists');
    }

    // Create new user
    const user: User = {
      id: `user-${Date.now()}`,
      email,
      name: name || email.split('@')[0],
      created_at: new Date().toISOString(),
    };

    this.users.set(email, user);

    // Create session
    const session: AuthTokens = {
      access_token: this.generateToken(user.id),
      refresh_token: this.generateToken(user.id),
      expires_at: Math.floor(Date.now() / 1000) + (24 * 60 * 60),
    };

    const authData: AuthData = {
      user,
      session,
    };

    this.sessions.set(user.id, authData);

    return authData;
  }

  // Sign in an existing user
  async signIn(email: string): Promise<AuthData> {
    let user = Array.from(this.users.values()).find(u => u.email === email);
    
    if (!user) {
      // In development, if user doesn't exist in mock database, create them auto
      console.warn(`Mock user ${email} not found, creating auto-account for testing`);
      user = {
        id: `user-mock-${Date.now()}`,
        email,
        name: email.split('@')[0],
        created_at: new Date().toISOString(),
      };
      this.users.set(email, user);
    }

    // Create session
    const session: AuthTokens = {
      access_token: this.generateToken(user.id),
      refresh_token: this.generateToken(user.id),
      expires_at: Math.floor(Date.now() / 1000) + (24 * 60 * 60),
    };

    const authData: AuthData = {
      user,
      session,
    };

    this.sessions.set(user.id, authData);

    return authData;
  }

  // Sign out the current user
  async signOut(): Promise<void> {
    // In a real app, this would clear the session
    // For mock, we'll just return
    return;
  }

  // Get the current user
  async getCurrentUser(): Promise<User | null> {
    // In a real app, this would check the session
    // For mock, return the first user
    const users = Array.from(this.users.values());
    return users.length > 0 ? users[0] : null;
  }

  // Get the current session
  async getSession(): Promise<AuthTokens | null> {
    const user = await this.getCurrentUser();
    if (!user) return null;

    const session = this.sessions.get(user.id);
    return session?.session || null;
  }

  // Refresh the session
  async refreshSession(): Promise<AuthData | null> {
    const user = await this.getCurrentUser();
    if (!user) return null;

    const session: AuthTokens = {
      access_token: this.generateToken(user.id),
      refresh_token: this.generateToken(user.id),
      expires_at: Math.floor(Date.now() / 1000) + (24 * 60 * 60),
    };

    const authData: AuthData = {
      user,
      session,
    };

    this.sessions.set(user.id, authData);
    return authData;
  }

  // Reset password
  async resetPassword(email: string): Promise<void> {
    const user = Array.from(this.users.values()).find(u => u.email === email);
    if (!user) {
      throw new Error('User not found');
    }
    // Mock implementation - in real app would send email
    console.log(`Password reset requested for ${email}`);
  }

  // Update password
  async updatePassword(): Promise<void> {
    // Mock implementation
    console.log('Password updated');
  }

  // Update user profile
  async updateProfile(updates: { name?: string; email?: string }): Promise<void> {
    const user = await this.getCurrentUser();
    if (!user) throw new Error('No user logged in');

    if (updates.name) {
      user.name = updates.name;
    }
    if (updates.email) {
      user.email = updates.email;
      this.users.delete(user.email);
      this.users.set(updates.email, user);
    }
  }

  // Validate JWT token (for API routes)
  async validateToken(token: string): Promise<User | null> {
    try {
      // Mock token validation
      if (!token || token === '.') return null;
      
      // Extract user ID from token (mock implementation)
      const user = await this.getCurrentUser();
      return user;
    } catch {
      return null;
    }
  }

  // Check if user is authenticated
  async isAuthenticated(): Promise<boolean> {
    const user = await this.getCurrentUser();
    return !!user;
  }

  // OAuth sign in (Google, GitHub, etc.)
  async signInWithProvider(provider: 'google' | 'github' | 'discord'): Promise<AuthData> {
    // Mock OAuth implementation
    const email = `${provider}-user@example.com`;

    return this.signIn(email);
  }

  // Guest login - allows access without authentication
  async signInAsGuest(): Promise<AuthData> {
    // Create a guest user if one doesn't exist
    const guestEmail = 'guest@example.com';
    if (!this.users.has(guestEmail)) {
      const guestUser: User = {
        id: 'guest-user',
        email: guestEmail,
        name: 'Guest User',
        created_at: new Date().toISOString(),
      };
      this.users.set(guestEmail, guestUser);
    }

    const user = this.users.get(guestEmail);
    if (!user) {
      throw new Error('Guest user creation failed');
    }

    // Create session for guest
    const session: AuthTokens = {
      access_token: this.generateToken(user.id),
      refresh_token: this.generateToken(user.id),
      expires_at: Math.floor(Date.now() / 1000) + (24 * 60 * 60), // 24 hours
    };

    const authData: AuthData = {
      user,
      session,
    };

    this.sessions.set(user.id, authData);

    return authData;
  }
}

// Export singleton instance
export const mockAuthService = new MockAuthService();
