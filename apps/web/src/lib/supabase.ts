import { createClient } from '@supabase/supabase-js';
import { devWarn } from '../utils/dev-log';
import type { User as AppUser } from '../types/api';

// Local shape instead of importing User from @supabase/supabase-js — Vercel's
// pnpm hoisting produces a second copy of the package whose type exports are
// incomplete, causing TS2305 errors on any named import from it.
interface SupabaseUser {
  id: string;
  email?: string;
  user_metadata?: Record<string, unknown>;
  role?: string;
  created_at: string;
}

const supabaseUrl = process.env['NEXT_PUBLIC_SUPABASE_URL'];
const supabaseAnonKey = process.env['NEXT_PUBLIC_SUPABASE_ANON_KEY'];

if (!supabaseUrl || !supabaseAnonKey) {
  devWarn(
    '[supabase] NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY not set — Realtime features disabled'
  );
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
    name:
      (u.user_metadata?.['name'] as string | undefined) ??
      (u.user_metadata?.['full_name'] as string | undefined),
    role: u.role ?? 'authenticated',
    created_at: u.created_at,
  };
}

// Wrapped auth helpers — callers import these instead of accessing supabase.auth
// directly, which prevents Vercel's duplicate-package type resolution from
// losing methods like signUp off the SupabaseAuthClient interface.
export async function authSignUp(email: string, password: string, captchaToken?: string) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    ...(captchaToken ? { options: { captchaToken } } : {}),
  });
  return { session: data?.session ?? null, error };
}

export async function authSignIn(email: string, password: string, captchaToken?: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
    ...(captchaToken ? { options: { captchaToken } } : {}),
  });
  return { session: data?.session ?? null, error };
}

export async function authSignInWithOAuth(provider: string, redirectTo: string) {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: provider as Parameters<typeof supabase.auth.signInWithOAuth>[0]['provider'],
    options: { redirectTo },
  });
  return { data, error };
}

export async function authGetSession() {
  const { data, error } = await supabase.auth.getSession();
  return { session: data?.session ?? null, error };
}

export async function authUpdateUser(attributes: {
  data?: Record<string, unknown>;
  email?: string;
}) {
  const { data, error } = await supabase.auth.updateUser(attributes);
  return { user: data?.user ?? null, error };
}

export async function authSignOut() {
  const { error } = await supabase.auth.signOut();
  return { error };
}

export async function authRefreshSession() {
  const { data, error } = await supabase.auth.refreshSession();
  return { session: data?.session ?? null, error };
}

export async function authExchangeCodeForSession(code: string) {
  const { data, error } = await supabase.auth.exchangeCodeForSession(code);
  return { session: data?.session ?? null, error };
}

export function authOnStateChange(
  callback: (event: string, session: { access_token: string; user: SupabaseUser } | null) => void
) {
  const { data } = supabase.auth.onAuthStateChange((event, session) =>
    callback(event, session as { access_token: string; user: SupabaseUser } | null)
  );
  return () => data.subscription.unsubscribe();
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
