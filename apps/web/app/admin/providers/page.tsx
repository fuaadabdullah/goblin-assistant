'use client';

import { Suspense } from 'react';
import ProvidersPage from '@/screens/EnhancedProvidersPage';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export const dynamic = 'force-dynamic';

const AdminProvidersContent = withRouteErrorBoundary(function AdminProvidersContent() {
  return <ProvidersPage />;
}, 'adminProviders');

export default function AdminProviders() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg" />}>
      <AdminLayout fullWidth>
        <AdminProvidersContent />
      </AdminLayout>
    </Suspense>
  );
}
