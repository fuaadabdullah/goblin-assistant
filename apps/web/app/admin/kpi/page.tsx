'use client';

import { Suspense } from 'react';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';
import KpiDashboard from '@/features/admin/kpi/KpiDashboard';

export const dynamic = 'force-dynamic';

const KpiContent = withRouteErrorBoundary(function KpiContent() {
  return <KpiDashboard />;
}, 'adminKpi');

export default function KpiPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading…</div>}>
      <AdminLayout mainId="kpi-content" mainLabel="KPI Dashboard">
        <KpiContent />
      </AdminLayout>
    </Suspense>
  );
}
