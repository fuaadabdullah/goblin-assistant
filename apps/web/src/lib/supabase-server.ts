import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

/**
 * Creates a Supabase client for use in Next.js middleware (Edge runtime).
 *
 * Returns both the client and a mutable `response` object. The `setAll`
 * callback keeps refreshed session cookies flowing back to the browser —
 * callers must return the returned `response` (or merge its cookies) rather
 * than a fresh `NextResponse.next()`.
 */
export function createSupabaseMiddlewareClient(request: NextRequest): {
  supabase: ReturnType<typeof createServerClient>;
  getResponse: () => NextResponse;
} {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env['NEXT_PUBLIC_SUPABASE_URL'] ?? 'https://placeholder.supabase.co',
    process.env['NEXT_PUBLIC_SUPABASE_ANON_KEY'] ?? 'placeholder',
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  return { supabase, getResponse: () => response };
}
