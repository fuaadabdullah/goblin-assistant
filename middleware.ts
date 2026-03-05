// middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * HMAC-SHA256 JWT verification using Web Crypto API (Edge Runtime compatible).
 * Validates both the signature and standard claims (exp, structure).
 */
async function verifyJWT(token: string, secret: string): Promise<{ isValid: boolean; payload?: any }> {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) {
      return { isValid: false };
    }

    const [headerB64, payloadB64, signatureB64] = parts;

    // Import the secret key for HMAC-SHA256
    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(secret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['verify']
    );

    // Decode the signature from base64url
    const signatureStr = signatureB64.replace(/-/g, '+').replace(/_/g, '/');
    const signatureBytes = Uint8Array.from(atob(signatureStr), c => c.charCodeAt(0));

    // Verify the HMAC signature over "header.payload"
    const data = encoder.encode(`${headerB64}.${payloadB64}`);
    const valid = await crypto.subtle.verify('HMAC', key, signatureBytes, data);

    if (!valid) {
      return { isValid: false };
    }

    // Decode and parse payload
    const payload = JSON.parse(atob(payloadB64.replace(/-/g, '+').replace(/_/g, '/')));

    // Check expiration
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp && payload.exp < now) {
      return { isValid: false };
    }

    return { isValid: true, payload };
  } catch {
    return { isValid: false };
  }
}

// Routes that require authentication
const protectedRoutes = [
  '/api/analytics',
  '/settings',
];

// Routes that require admin role
const adminRoutes = [
  '/admin',
];

// Routes that are public (exact matches or prefixes)
const publicRoutes = [
  '/login',
  '/register',
  '/api/auth',
  '/api/chat', // Chat API endpoint - public for demo purposes
  '/api/providers', // Providers API - public
  '/api/routing', // Routing API - public
  '/',
  '/chat', // Allow direct access to chat for demo purposes
  '/dashboard', // Dashboard now redirects to chat
  '/api/health', // Health check should be public
  '/health', // Health check direct path
];

// Routes that should never require auth (even for sub-paths)
const alwaysPublicRoutes = [
  '/_next/static',
  '/_next/image',
  '/favicon.ico',
  '/public',
  '/api/health',
];

function isAdminRoute(pathname: string): boolean {
  const normalizedPath = pathname.replace(/\/+/g, '/').replace(/\/$/, '');
  return adminRoutes.some(route => normalizedPath.startsWith(route));
}

function isProtectedRoute(pathname: string): boolean {
  // Normalize pathname to prevent bypass attempts
  const normalizedPath = pathname.replace(/\/+/g, '/').replace(/\/$/, '');

  // Always allow certain routes
  if (alwaysPublicRoutes.some(route => normalizedPath.startsWith(route))) {
    return false;
  }

  // Check exact public route matches
  if (publicRoutes.includes(normalizedPath)) {
    return false;
  }

  // Check public route prefixes
  if (publicRoutes.some(route => normalizedPath.startsWith(route + '/'))) {
    return false;
  }

  // Check if it's a protected route or admin route
  return protectedRoutes.some(route => normalizedPath.startsWith(route)) || isAdminRoute(normalizedPath);
}

// JWT Configuration - don't throw during initialization
const JWT_SECRET = process.env.JWT_SECRET_KEY;

async function verifyToken(token: string): Promise<{ isValid: boolean; payload?: any }> {
  // SECURITY: If no JWT secret is configured, deny all protected requests
  if (!JWT_SECRET) {
    console.warn('JWT_SECRET_KEY is not configured — denying protected request');
    return { isValid: false };
  }

  try {
    const validation = await verifyJWT(token, JWT_SECRET);

    if (!validation.isValid) {
      return { isValid: false };
    }

    const payload = validation.payload;

    // Additional validation checks
    if (typeof payload !== 'object' || payload === null) {
      return { isValid: false };
    }

    // Check if token has required fields
    if (!payload.sub || !payload.exp) {
      return { isValid: false };
    }

    // Check if token is expired (with 5 minute buffer)
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp < (now - 300)) { // 5 minute buffer for clock skew
      return { isValid: false };
    }

    return { isValid: true, payload };
  } catch (error) {
    return { isValid: false };
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Check if the route requires authentication using the secure function
  const requiresAuth = isProtectedRoute(pathname);

  // Allow public routes
  if (!requiresAuth) {
    return NextResponse.next();
  }

  // For protected routes, check authentication
  const authToken = request.cookies.get('auth-token')?.value ||
                   request.headers.get('authorization')?.replace('Bearer ', '');

  if (!authToken) {
    // Redirect to login for browser requests
    if (request.headers.get('accept')?.includes('text/html')) {
      return NextResponse.redirect(new URL('/login', request.url));
    }

    // Return 401 for API requests
    return NextResponse.json(
      { error: 'Authentication required' },
      { status: 401 }
    );
  }

  // Validate the JWT token
  const tokenValidation = await verifyToken(authToken);
  if (!tokenValidation.isValid) {
    // Redirect to login for browser requests
    if (request.headers.get('accept')?.includes('text/html')) {
      return NextResponse.redirect(new URL('/login', request.url));
    }

    // Return 401 for API requests
    return NextResponse.json(
      { error: 'Invalid or expired authentication token' },
      { status: 401 }
    );
  }

  // Check admin role for admin routes
  if (isAdminRoute(pathname)) {
    const payload = tokenValidation.payload;
    const userRole = payload?.role || payload?.user_role || 'user';
    const isAdmin = userRole === 'admin' || userRole === 'superadmin' || payload?.is_admin === true;
    
    if (!isAdmin) {
      // Redirect non-admins to chat (forbidden from admin area)
      if (request.headers.get('accept')?.includes('text/html')) {
        return NextResponse.redirect(new URL('/chat?error=admin_required', request.url));
      }
      
      // Return 403 for API requests
      return NextResponse.json(
        { error: 'Admin access required' },
        { status: 403 }
      );
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes - these are proxied to backend)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - health (health check endpoint)
     * - public files with extensions
     */
    '/((?!api|_next/static|_next/image|favicon.ico|health|.*\\.).*)',
  ],
};
