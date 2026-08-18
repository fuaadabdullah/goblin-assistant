'use client';

import { Suspense } from 'react';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';
import PilotKitScreen from '@/features/admin/pilot/PilotKitScreen';

export const dynamic = 'force-dynamic';

const PilotKitContent = withRouteErrorBoundary(function PilotKitContent() {
  return <PilotKitScreen />;
}, 'adminPilot');

export default function PilotPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading…</div>}>
      <AdminLayout mainId="pilot-content" mainLabel="Pilot Kit">
        <PilotKitContent />
      </AdminLayout>
    </Suspense>
  );
}
