import { createClient } from '@supabase/supabase-js';
import type { User as SupabaseUser } from '@supabase/supabase-js';
import { devWarn } from '../utils/dev-log';
import type { User as AppUser } from '../types/api';

const supabaseUrl = process.env['NEXT_PUBLIC_SUPABASE_URL'];
const supabaseAnonKey = process.env['NEXT_PUBLIC_SUPABASE_ANON_KEY'];

if (!supabaseUrl || !supabaseAnonKey) {
  devWarn('[supabase] NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY not set — Realtime features disabled');
}

export const supabase = createClient(
  supabaseUrl ?? 'https://placeholder.supabase.co',
  supabaseAnonKey ?? 'placeholder',
  {
    realtime: { params: { eventsPerSecond: 10 } },
  }
);

export const supabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey);

export function supabaseUserToAppUser(u: SupabaseUser): AppUser {
  return {
    id: u.id,
    email: u.email ?? '',
    name: (u.user_metadata?.['name'] as string | undefined) ?? u.user_metadata?.['full_name'] as string | undefined,
    role: u.role ?? 'authenticated',
    created_at: u.created_at,
  };
}

export interface ProviderStatusRow {
  provider: string;
  is_healthy: boolean;
  circuit_state: string;
  failure_count: number;
  avg_latency_ms: number | null;
  error_message: string | null;
  checked_at: string;
}
