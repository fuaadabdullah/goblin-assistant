import type { FC } from 'react';
import { useRouter } from 'next/router';
import { useAuthSession } from '../../hooks/api/useAuthSession';
import { isAdminUser } from '../../utils/access';
import { useChatSession } from './hooks/useChatSession';
import ChatView from './components/ChatView';

const ChatScreen: FC = () => {
  const { user, isAuthenticated } = useAuthSession();
  const router = useRouter();
  const session = useChatSession();
  const isGuest = !isAuthenticated && router.query.guest === '1';

  return <ChatView session={session} isAdmin={isAdminUser(user)} isGuest={isGuest} />;
};

export default ChatScreen;
