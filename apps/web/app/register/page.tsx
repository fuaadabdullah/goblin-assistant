'use client';

import LoginPage from '@/screens/LoginPage';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

function RegisterPage() {
  return <LoginPage initialMode="register" />;
}

export default withRouteErrorBoundary(RegisterPage, 'register');
