'use client';

import { Suspense } from 'react';
import ChatPageScreen from '@/screens/ChatPage';
import { withRouteErrorBoundary } from '@/components/RouteBoundary';

export const dynamic = 'force-dynamic';

const ChatPageContent = withRouteErrorBoundary(ChatPageScreen, 'chat');

export default function ChatPageRoute() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg" />}>
      <ChatPageContent />
    </Suspense>
  );
}
