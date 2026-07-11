'use client';

import { Suspense } from 'react';
import SandboxPageScreen from '@/screens/SandboxPage';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export const dynamic = 'force-dynamic';

const SandboxPageContent = withRouteErrorBoundary(SandboxPageScreen, 'sandbox');

export default function SandboxPageRoute() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg" />}>
      <SandboxPageContent />
    </Suspense>
  );
}
