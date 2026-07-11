'use client';

import { Suspense } from 'react';
import HelpPageScreen from '@/screens/HelpPage';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export const dynamic = 'force-dynamic';

const HelpPageContent = withRouteErrorBoundary(HelpPageScreen, 'help');

export default function HelpPageRoute() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg" />}>
      <HelpPageContent />
    </Suspense>
  );
}
