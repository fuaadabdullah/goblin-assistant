'use client';

import { Suspense } from 'react';
import nextDynamic from 'next/dynamic';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';
import PageState from '@/components/ui/PageState';

export const dynamic = 'force-dynamic';

const SettingsPage = nextDynamic(() => import('@/screens/SettingsPage'), {
  ssr: false,
  loading: () => (
    <PageState
      variant="loading"
      title="Loading settings"
      description="Preparing provider and account controls."
    />
  ),
});

const AdminSettingsContent = withRouteErrorBoundary(function AdminSettingsContent() {
  return <SettingsPage />;
}, 'adminSettings');

export default function AdminSettings() {
  return (
    <Suspense fallback={<PageState variant="loading" title="Loading settings" description="Preparing provider and account controls." />}>
      <AdminLayout mainId="main-content" mainLabel="Admin Settings">
        <AdminSettingsContent />
      </AdminLayout>
    </Suspense>
  );
}
