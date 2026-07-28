'use client';

import { Suspense } from 'react';
import GoogleCallbackScreen from '@/screens/GoogleCallback';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export const dynamic = 'force-dynamic';

const GoogleCallbackContent = withRouteErrorBoundary(GoogleCallbackScreen, 'googleCallback');

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg" />}>
      <GoogleCallbackContent />
    </Suspense>
  );
}
