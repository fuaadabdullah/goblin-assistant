'use client';

import type { FC } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuthSession } from '../../hooks/api/useAuthSession';
import { useChatSession } from './hooks/useChatSession';
import ChatView from './components/ChatView';

const ChatScreen: FC = () => {
  const { isAuthenticated, isAdmin } = useAuthSession();
  const searchParams = useSearchParams();
  const isGuest = !isAuthenticated && searchParams.get('guest') === '1';
  const session = useChatSession({ loadThreads: !isGuest });

  return <ChatView session={session} isAdmin={isAdmin} isGuest={isGuest} />;
};

export default ChatScreen;
