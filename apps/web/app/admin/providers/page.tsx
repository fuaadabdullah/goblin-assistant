'use client';

import ProvidersPage from '@/screens/EnhancedProvidersPage';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

const AdminProvidersContent = withRouteErrorBoundary(function AdminProvidersContent() {
  return <ProvidersPage />;
}, 'adminProviders');

export default function AdminProviders() {
  return (
    <AdminLayout fullWidth>
      <AdminProvidersContent />
    </AdminLayout>
  );
}
