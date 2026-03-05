"use client";

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

/**
 * Dashboard Page - Redirects to Chat
 * The main customer experience is the chat interface.
 * System dashboard is now at /admin/dashboard for internal use only.
 */
export default function DashboardPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to chat - the main customer experience
    router.replace('/chat');
  }, [router]);

  // Show brief loading state during redirect
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
      <div className="text-white text-center">
        <div className="animate-spin w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full mx-auto mb-4"></div>
        <p className="text-slate-300">Redirecting to chat...</p>
      </div>
    </div>
  );
}
