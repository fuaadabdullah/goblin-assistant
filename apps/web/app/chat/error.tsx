'use client';

import { RouteBoundaryFallback, formatBoundaryTechnicalDetail } from '@/components/RouteBoundary';

export default function ChatError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <RouteBoundaryFallback
      title="Chat is temporarily unavailable"
      description="A rendering error occurred in the conversation workspace."
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