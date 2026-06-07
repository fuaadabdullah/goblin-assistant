'use client';

import { RouteBoundaryFallback, formatBoundaryTechnicalDetail } from '@/components/RouteBoundary';

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <RouteBoundaryFallback
      title="Admin dashboard is unavailable"
      description="A rendering error occurred in the admin area."
      actions={[
        { type: 'reload', label: 'Try Again', variant: 'primary' },
        { type: 'link', label: 'Back to Admin', href: '/admin', variant: 'secondary' },
        { type: 'link', label: 'Go Home', href: '/', variant: 'secondary' },
      ]}
      technicalDetail={formatBoundaryTechnicalDetail(error)}
      onReset={reset}
    />
  );
}