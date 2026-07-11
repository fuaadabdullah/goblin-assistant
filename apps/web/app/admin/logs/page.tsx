'use client';

import { Suspense } from 'react';
import LogsPage from '@/screens/LogsPage';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export const dynamic = 'force-dynamic';

const AdminLogsContent = withRouteErrorBoundary(function AdminLogsContent() {
  return <LogsPage />;
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
