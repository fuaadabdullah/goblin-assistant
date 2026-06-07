'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { MessageSquare } from 'lucide-react';
import { useUIStore } from '../store/uiStore';
import { trackEvent } from '../utils/analytics';

const ChatFAB: React.FC = () => {
  const setChatOpen = useUIStore((s) => s.setChatSidebarOpen);
  const router = useRouter();

  const handleClick = async () => {
    // Navigate to chat page first so the chat view is mounted, then open the drawer
    try {
      await router.push('/chat');
    } catch {
      // ignore navigation errors
    }
    trackEvent('chat_fab_clicked');
    setChatOpen(true);
  };

  return (
    <div className="fixed bottom-5 right-4 z-60 md:hidden">
      <button
        aria-label="Open Chat"
        onClick={handleClick}
        className="inline-flex items-center justify-center h-14 w-14 rounded-full bg-primary text-white shadow-glow-primary hover:brightness-95 active:scale-95 transition-transform focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
      >
        <MessageSquare className="w-6 h-6" aria-hidden="true" />
      </button>
    </div>
  );
};

export default ChatFAB;
