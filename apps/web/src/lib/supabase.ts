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

// Wrapped auth helpers — callers import these instead of accessing supabase.auth
// directly, which prevents Vercel's duplicate-package type resolution from
// losing methods like signUp off the SupabaseAuthClient interface.
export async function authSignUp(email: string, password: string) {
  const { data, error } = await supabase.auth.signUp({ email, password });
  return { session: data?.session ?? null, error };
}

export async function authSignIn(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  return { session: data?.session ?? null, error };
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
