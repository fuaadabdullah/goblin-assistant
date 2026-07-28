'use client';

import { Suspense } from 'react';
import LoginPage from '@/screens/LoginPage';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export const dynamic = 'force-dynamic';

const RegisterContent = withRouteErrorBoundary(function RegisterContent() {
  return <LoginPage initialMode="register" />;
}, 'register');

function RegisterPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg" />}>
      <RegisterContent />
    </Suspense>
  );
}

export default RegisterPage;
