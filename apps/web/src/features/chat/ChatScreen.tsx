'use client';

import type { FC } from 'react';
import { useSearchParams } from 'next/navigation';
import { useAuthSession } from '../../hooks/api/useAuthSession';
import { isAdminUser } from '../../utils/access';
import { useChatSession } from './hooks/useChatSession';
import ChatView from './components/ChatView';

const ChatScreen: FC = () => {
  const { user, isAuthenticated } = useAuthSession();
  const searchParams = useSearchParams();
  const session = useChatSession();
  const isGuest = !isAuthenticated && searchParams.get('guest') === '1';

  return <ChatView session={session} isAdmin={isAdminUser(user)} isGuest={isGuest} />;
};

export default ChatScreen;
