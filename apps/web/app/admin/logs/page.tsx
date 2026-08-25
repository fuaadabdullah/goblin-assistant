'use client';

import { Suspense } from 'react';
import nextDynamic from 'next/dynamic';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export const dynamic = 'force-dynamic';

const MonitoringScreen = nextDynamic(() => import('@/screens/MonitoringScreen'), {
  ssr: false,
  loading: () => <div className="min-h-screen bg-bg" />,
});

const AdminLogsContent = withRouteErrorBoundary(function AdminLogsContent() {
  return <MonitoringScreen />;
}, 'adminLogs');

export default function AdminLogs() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg" />}>
      <AdminLayout fullWidth>
        <AdminLogsContent />
      </AdminLayout>
    </Suspense>
  );
}
