// app/lib/services/database.ts
import { createClient, SupabaseClient } from '@supabase/supabase-js';

// Accept either NEXT_PUBLIC_* (used by Next.js for client exposure) or
// the unprefixed SUPABASE_* names (used by deployment scripts / CI).
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? process.env.SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? process.env.SUPABASE_ANON_KEY;
const supabaseServiceKey =
  process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_SERVICE_KEY ?? process.env.SUPABASE_SERVICE_ROLE;

// Lazy-initialize Supabase clients to avoid build-time errors
let _supabase: SupabaseClient | null = null;
let _supabaseAdmin: SupabaseClient | null = null;

function getSupabaseClient(): SupabaseClient {
  if (!_supabase) {
    if (!supabaseUrl || !supabaseAnonKey) {
      throw new Error(
        'Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY (for client) or SUPABASE_URL and SUPABASE_ANON_KEY (for deployment).',
      );
    }
    _supabase = createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: true,
      },
    });
  }
  return _supabase;
}

function getSupabaseAdmin(): SupabaseClient {
  if (!_supabaseAdmin) {
    if (!supabaseUrl || !supabaseAnonKey) {
      throw new Error(
        'Missing Supabase environment variables. Please set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY (for client) or SUPABASE_URL and SUPABASE_ANON_KEY (for deployment).',
      );
    }
    _supabaseAdmin = createClient(supabaseUrl, supabaseServiceKey || supabaseAnonKey, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });
  }
  return _supabaseAdmin;
}

// Client-side Supabase client (for browser) - lazy getter
export const supabase: SupabaseClient = new Proxy({} as SupabaseClient, {
  get(_, prop) {
    return (getSupabaseClient() as unknown as Record<string, unknown>)[prop as string];
  },
});

// Server-side Supabase client (for API routes) - lazy getter
export const supabaseAdmin: SupabaseClient = new Proxy({} as SupabaseClient, {
  get(_, prop) {
    return (getSupabaseAdmin() as unknown as Record<string, unknown>)[prop as string];
  },
});

// Database table names
export const TABLES = {
  USAGE_LOGS: 'usage_logs',
  COST_LOGS: 'cost_logs',
  PROVIDER_HEALTH: 'provider_health',
  USER_SESSIONS: 'user_sessions',
  CONVERSATIONS: 'conversations',
  MESSAGES: 'messages',
} as const;


// Helper functions for common database operations
export class DatabaseService {
  private client: SupabaseClient;

  constructor(client: SupabaseClient = supabaseAdmin) {
    this.client = client;
  }

  // Usage Analytics
  async getUsageStats(userId?: string, startDate?: Date, endDate?: Date) {
    let query = this.client
      .from(TABLES.USAGE_LOGS)
      .select('*')
      .order('created_at', { ascending: false });

    if (userId) {
      query = query.eq('user_id', userId);
    }

    if (startDate) {
      query = query.gte('created_at', startDate.toISOString());
    }

    if (endDate) {
      query = query.lte('created_at', endDate.toISOString());
    }

    const { data, error } = await query.limit(1000);

    if (error) {
      console.error('Error fetching usage stats:', error);
      return null;
    }

    return data;
  }

  // Cost Analytics
  async getCostStats(userId?: string, startDate?: Date, endDate?: Date) {
    let query = this.client
      .from(TABLES.COST_LOGS)
      .select('*')
      .order('created_at', { ascending: false });

    if (userId) {
      query = query.eq('user_id', userId);
    }

    if (startDate) {
      query = query.gte('created_at', startDate.toISOString());
    }

    if (endDate) {
      query = query.lte('created_at', endDate.toISOString());
    }

    const { data, error } = await query.limit(1000);

    if (error) {
      console.error('Error fetching cost stats:', error);
      return null;
    }

    return data;
  }

  // Provider Health
  async getProviderHealth() {
    const { data, error } = await this.client
      .from(TABLES.PROVIDER_HEALTH)
      .select('*')
      .order('last_checked', { ascending: false });

    if (error) {
      console.error('Error fetching provider health:', error);
      return null;
    }

    return data;
  }

  // Log usage event
  async logUsage(userId: string, provider: string, model: string, tokens: number, cost: number, latency: number) {
    const { error } = await this.client
      .from(TABLES.USAGE_LOGS)
      .insert({
        user_id: userId,
        provider,
        model,
        tokens_used: tokens,
        cost,
        latency_ms: latency,
        created_at: new Date().toISOString(),
      });

    if (error) {
      console.error('Error logging usage:', error);
      return false;
    }

    return true;
  }

  // Log cost event
  async logCost(userId: string, provider: string, amount: number, currency: string = 'USD') {
    const { error } = await this.client
      .from(TABLES.COST_LOGS)
      .insert({
        user_id: userId,
        provider,
        amount,
        currency,
        created_at: new Date().toISOString(),
      });

    if (error) {
      console.error('Error logging cost:', error);
      return false;
    }

    return true;
  }

  // Update provider health
  async updateProviderHealth(providerId: string, status: string, latency: number, errorRate: number) {
    const { error } = await this.client
      .from(TABLES.PROVIDER_HEALTH)
      .upsert({
        provider_id: providerId,
        status,
        latency_ms: latency,
        error_rate: errorRate,
        last_checked: new Date().toISOString(),
        uptime_percentage: status === 'healthy' ? 99.9 : 95.0, // Simplified calculation
      });

    if (error) {
      console.error('Error updating provider health:', error);
      return false;
    }

    return true;
  }
}

// Export singleton instance
export const db = new DatabaseService();
