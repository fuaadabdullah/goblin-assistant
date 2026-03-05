#!/usr/bin/env tsx
import { createClient } from '@supabase/supabase-js';

async function main() {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? process.env.SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? process.env.SUPABASE_ANON_KEY;
  const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY ?? process.env.SUPABASE_SERVICE_KEY;

  console.log('Supabase URL:', supabaseUrl ? supabaseUrl : '(missing)');
  console.log('Supabase ANON Key:', supabaseAnonKey ? 'present' : '(missing)');
  console.log('Supabase SERVICE Role Key:', supabaseServiceKey ? 'present' : '(missing)');
  console.log('Env vars check: SUPABASE_URL set?', !!process.env.SUPABASE_URL, 'SUPABASE_ANON_KEY set?', !!process.env.SUPABASE_ANON_KEY);

  if (!supabaseUrl || !supabaseAnonKey) {
    console.error('\nMissing required Supabase environment variables. Create apps/goblin-assistant/.env.local or export SUPABASE_URL and SUPABASE_ANON_KEY.');
    process.exit(1);
  }

  console.log('\nAttempting basic Supabase connectivity test...');

  // Create a lightweight client here to avoid importing the app's database module
  const client = createClient(supabaseUrl, supabaseServiceKey || supabaseAnonKey);

  try {
    // Try a basic auth test - get the current user (should work with anon key)
    const { error } = await client.auth.getUser();
    
    if (error && error.message !== 'Auth session missing!') {
      console.error('Auth test error:', error.message || error);
      process.exit(2);
    }
    
    console.log('✅ Basic Supabase connectivity test passed (auth endpoint accessible).');
    console.log('Note: getUser() returns null when not authenticated, which is expected.');
    process.exit(0);
  } catch (err) {
    console.error('Unexpected error during connectivity test:', err);
    process.exit(3);
  }
}

main();
