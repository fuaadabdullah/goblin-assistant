'use client';

import { Suspense } from 'react';
import nextDynamic from 'next/dynamic';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';
import { DashboardSkeleton } from '@/components/LoadingSkeleton';

export const dynamic = 'force-dynamic';

const Dashboard = nextDynamic(() => import('@/screens/Dashboard'), {
  ssr: false,
  loading: () => <DashboardSkeleton />,
});

const AdminDashboardContent = withRouteErrorBoundary(function AdminDashboardContent() {
  return <Dashboard />;
}, 'adminIndex');

export default function Admin() {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <AdminLayout mainId="main-content" mainLabel="Admin Dashboard">
        <AdminDashboardContent />
      </AdminLayout>
    </Suspense>
  );
}
