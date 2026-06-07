'use client';

import dynamic from 'next/dynamic';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';
import { DashboardSkeleton } from '@/components/LoadingSkeleton';

const EnhancedDashboard = dynamic(() => import('@/components/EnhancedDashboard'), {
  ssr: false,
  loading: () => <DashboardSkeleton />,
});

const AdminDashboardContent = withRouteErrorBoundary(function AdminDashboardContent() {
  return <EnhancedDashboard />;
}, 'adminIndex');

export default function Admin() {
  return (
    <AdminLayout mainId="main-content" mainLabel="Admin Dashboard">
      <AdminDashboardContent />
    </AdminLayout>
  );
}
