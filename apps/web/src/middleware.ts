import { NextRequest, NextResponse } from 'next/server';

const PROTECTED_PREFIXES = ['/chat', '/account', '/admin', '/settings', '/search', '/sandbox'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));

  if (isProtected && !request.cookies.get('goblin_auth')) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|login|register|google-callback|help|startup|onboarding).*)'],
};
