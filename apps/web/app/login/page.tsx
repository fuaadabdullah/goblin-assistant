'use client';

import { Suspense } from 'react';
import LoginPageScreen from '@/screens/LoginPage';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export const dynamic = 'force-dynamic';

const LoginPageContent = withRouteErrorBoundary(LoginPageScreen, 'login');

export default function LoginPageRoute() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg" />}>
      <LoginPageContent />
    </Suspense>
  );
}
