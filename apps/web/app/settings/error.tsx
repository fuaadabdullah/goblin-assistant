'use client';

import { RouteBoundaryFallback, formatBoundaryTechnicalDetail } from '@/components/RouteBoundary';

export default function SettingsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <RouteBoundaryFallback
      title="Settings are temporarily unavailable"
      description="A rendering error occurred in the settings area."
      actions={[
        { type: 'reload', label: 'Try Again', variant: 'primary' },
        { type: 'link', label: 'Go Home', href: '/', variant: 'secondary' },
        { type: 'link', label: 'Open Help', href: '/help', variant: 'secondary' },
      ]}
      technicalDetail={formatBoundaryTechnicalDetail(error)}
      onReset={reset}
    />
  );
}
