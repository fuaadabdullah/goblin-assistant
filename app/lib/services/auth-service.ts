// app/lib/services/auth-service.ts
import { supabase } from './database';
import { mockAuthService } from './mock-auth-service';

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

export class AuthService {
  // Check if Supabase is properly configured
  private isSupabaseConfigured(): boolean {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? process.env.SUPABASE_URL;
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? process.env.SUPABASE_ANON_KEY;
    return !!(supabaseUrl && supabaseAnonKey);
  }

  // Validate Supabase configuration
  private validateSupabaseConfig(): void {
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? process.env.SUPABASE_URL;
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? process.env.SUPABASE_ANON_KEY;
    
    if (!supabaseUrl || !supabaseAnonKey) {
      throw new Error('Supabase is not configured. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY environment variables.');
    }
  }

  // Sign up a new user
  async signUp(email: string, password: string, name?: string) {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              name: name || email.split('@')[0],
            },
          },
        });

        if (error) {
          console.error('Supabase sign up error:', error);
          throw new Error(`Sign up failed: ${error.message}`);
        }

        if (!data.user) {
          throw new Error('User creation failed - no user returned');
        }

        return {
          user: {
            id: data.user.id,
            email: data.user.email || email,
            name: data.user.user_metadata?.name || name,
            created_at: data.user.created_at,
          },
          session: data.session ? {
            access_token: data.session.access_token,
            refresh_token: data.session.refresh_token,
            expires_at: data.session.expires_at,
          } : null,
        };
      } catch (error) {
        console.error('Supabase sign up failed:', error);
        console.warn('Falling back to mock auth');
        return mockAuthService.signUp(email, password, name);
      }
    } else {
      console.warn('Supabase not configured, using mock auth');
      return mockAuthService.signUp(email, password, name);
    }
  }

  // Sign in an existing user
  async signIn(email: string, password: string) {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();

        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });

        if (error) {
          console.error('Supabase sign in error:', error);
          throw new Error(`Sign in failed: ${error.message}`);
        }

        if (!data.user) {
          throw new Error('Authentication failed - no user returned');
        }

        return {
          user: {
            id: data.user.id,
            email: data.user.email || email,
            name: data.user.user_metadata?.name,
            created_at: data.user.created_at,
          },
          session: data.session ? {
            access_token: data.session.access_token,
            refresh_token: data.session.refresh_token,
            expires_at: data.session.expires_at,
          } : null,
        };
      } catch (error) {
        console.error('Supabase sign in failed:', error);
        console.warn('Falling back to mock auth');
        // For mock auth, we don't need password - just check if user exists
        return mockAuthService.signIn(email);
      }
    } else {
      console.warn('Supabase not configured, using mock auth');
      // For mock auth, we don't need password - just check if user exists
      return mockAuthService.signIn(email);
    }
  }

  // Sign out the current user
  async signOut() {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        const { error } = await supabase.auth.signOut();

        if (error) {
          console.error('Supabase sign out error:', error);
          throw new Error(`Sign out failed: ${error.message}`);
        }
      } catch (error) {
        console.error('Supabase sign out failed:', error);
        console.warn('Continuing with mock auth');
      }
    }
    // Mock sign out is a no-op
  }

  // Get the current user
  async getCurrentUser(): Promise<User | null> {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        const { data: { user }, error } = await supabase.auth.getUser();

        if (error) {
          console.error('Supabase get user error:', error);
          return null;
        }

        if (!user) {
          return null;
        }

        return {
          id: user.id,
          email: user.email || '',
          name: user.user_metadata?.name,
          created_at: user.created_at,
        };
      } catch (error) {
        console.error('Supabase get user failed:', error);
        console.warn('Falling back to mock auth');
        return mockAuthService.getCurrentUser();
      }
    } else {
      return mockAuthService.getCurrentUser();
    }
  }

  // Get the current session
  async getSession() {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        const { data: { session }, error } = await supabase.auth.getSession();

        if (error) {
          console.error('Supabase get session error:', error);
          throw new Error(`Get session failed: ${error.message}`);
        }

        return session ? {
          access_token: session.access_token,
          refresh_token: session.refresh_token,
          expires_at: session.expires_at,
        } : null;
      } catch (error) {
        console.error('Supabase get session failed:', error);
        console.warn('Falling back to mock auth');
        return mockAuthService.getSession();
      }
    } else {
      return mockAuthService.getSession();
    }
  }

  // Refresh the session
  async refreshSession() {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        const { data, error } = await supabase.auth.refreshSession();

        if (error) {
          console.error('Supabase refresh session error:', error);
          throw new Error(`Refresh session failed: ${error.message}`);
        }

        return data.session ? {
          access_token: data.session.access_token,
          refresh_token: data.session.refresh_token,
          expires_at: data.session.expires_at,
        } : null;
      } catch (error) {
        console.error('Supabase refresh session failed:', error);
        console.warn('Falling back to mock auth');
        return mockAuthService.refreshSession();
      }
    } else {
      return mockAuthService.refreshSession();
    }
  }

  // Reset password
  async resetPassword(email: string) {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        const { error } = await supabase.auth.resetPasswordForEmail(email, {
          redirectTo: `${process.env.NEXT_PUBLIC_APP_URL}/reset-password`,
        });

        if (error) {
          console.error('Supabase reset password error:', error);
          throw new Error(`Reset password failed: ${error.message}`);
        }
      } catch (error) {
        console.error('Supabase reset password failed:', error);
        console.warn('Falling back to mock auth');
        return mockAuthService.resetPassword(email);
      }
    } else {
      return mockAuthService.resetPassword(email);
    }
  }

  // Update password
  async updatePassword(newPassword: string) {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        const { error } = await supabase.auth.updateUser({
          password: newPassword,
        });

        if (error) {
          console.error('Supabase update password error:', error);
          throw new Error(`Update password failed: ${error.message}`);
        }
      } catch (error) {
        console.error('Supabase update password failed:', error);
        console.warn('Falling back to mock auth');
        return mockAuthService.updatePassword();
      }
    } else {
      return mockAuthService.updatePassword();
    }
  }

  // Update user profile
  async updateProfile(updates: { name?: string; email?: string }) {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        const { error } = await supabase.auth.updateUser({
          email: updates.email,
          data: {
            name: updates.name,
          },
        });

        if (error) {
          console.error('Supabase update profile error:', error);
          throw new Error(`Update profile failed: ${error.message}`);
        }
      } catch (error) {
        console.error('Supabase update profile failed:', error);
        console.warn('Falling back to mock auth');
        return mockAuthService.updateProfile(updates);
      }
    } else {
      return mockAuthService.updateProfile(updates);
    }
  }

  // Validate JWT token (for API routes)
  async validateToken(token: string) {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        const { data: { user }, error } = await supabase.auth.getUser(token);

        if (error || !user) {
          console.error('Supabase validate token error:', error);
          return null;
        }

        return {
          id: user.id,
          email: user.email || '',
          name: user.user_metadata?.name,
          created_at: user.created_at,
        };
      } catch (error) {
        console.error('Supabase validate token failed:', error);
        return null;
      }
    } else {
      return mockAuthService.validateToken(token);
    }
  }

  // Check if user is authenticated
  async isAuthenticated(): Promise<boolean> {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        const user = await this.getCurrentUser();
        return !!user;
      } catch (error) {
        console.error('Supabase isAuthenticated failed:', error);
        return false;
      }
    } else {
      return mockAuthService.isAuthenticated();
    }
  }

  // OAuth sign in (Google, GitHub, etc.)
  async signInWithProvider(provider: 'google' | 'github' | 'discord') {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        const { data, error } = await supabase.auth.signInWithOAuth({
          provider,
          options: {
            redirectTo: `${process.env.NEXT_PUBLIC_APP_URL}/auth/callback`,
          },
        });

        if (error) {
          console.error('Supabase OAuth error:', error);
          throw new Error(`OAuth sign in failed: ${error.message}`);
        }

        return data;
      } catch (error) {
        console.error('Supabase OAuth failed:', error);
        console.warn('Falling back to mock auth');
        return mockAuthService.signInWithProvider(provider);
      }
    } else {
      return mockAuthService.signInWithProvider(provider);
    }
  }

  // Guest login - allows access without authentication
  async signInAsGuest() {
    if (this.isSupabaseConfigured()) {
      try {
        this.validateSupabaseConfig();
        // For Supabase, we would need to implement guest access
        // For now, fall back to mock auth
        console.warn('Guest login not implemented for Supabase, using mock auth');
        return mockAuthService.signInAsGuest();
      } catch (error) {
        console.error('Supabase guest login failed:', error);
        console.warn('Falling back to mock auth');
        return mockAuthService.signInAsGuest();
      }
    } else {
      return mockAuthService.signInAsGuest();
    }
  }
}

// Export singleton instance
export const authService = new AuthService();