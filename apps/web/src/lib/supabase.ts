import { createClient } from '@supabase/supabase-js';
import { devWarn } from '../utils/dev-log';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

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

export interface ProviderStatusRow {
  provider: string;
  is_healthy: boolean;
  circuit_state: string;
  failure_count: number;
  avg_latency_ms: number | null;
  error_message: string | null;
  checked_at: string;
}
