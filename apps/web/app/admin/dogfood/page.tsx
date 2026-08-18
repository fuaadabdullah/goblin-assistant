'use client';

import { Suspense } from 'react';
import AdminLayout from '@/layout/AdminLayout';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';
import DogfoodJournalScreen from '@/features/admin/dogfood/DogfoodJournalScreen';

export const dynamic = 'force-dynamic';

const DogfoodJournalContent = withRouteErrorBoundary(function DogfoodJournalContent() {
  return <DogfoodJournalScreen />;
}, 'adminDogfood');

export default function DogfoodPage() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">Loading…</div>}>
      <AdminLayout mainId="dogfood-content" mainLabel="Dogfood Journal">
        <DogfoodJournalContent />
      </AdminLayout>
    </Suspense>
  );
}
