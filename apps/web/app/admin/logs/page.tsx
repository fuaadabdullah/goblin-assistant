'use client';

import { Suspense } from 'react';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';
import MonitoringScreen from '@/screens/MonitoringScreen';

export const dynamic = 'force-dynamic';

const AdminMonitoringContent = withRouteErrorBoundary(function AdminMonitoringContent() {
  return <MonitoringScreen />;
}, 'adminLogs');

export default function AdminLogs() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg" />}>
      <AdminLayout fullWidth>
        <AdminMonitoringContent />
      </AdminLayout>
    </Suspense>
  );
}
