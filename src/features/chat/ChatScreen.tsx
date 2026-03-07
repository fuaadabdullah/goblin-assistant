import type { FC } from 'react';
import { useAuthSession } from '../../hooks/api/useAuthSession';
import { isAdminUser } from '../../utils/access';
import { useChatSession } from './hooks/useChatSession';
import ChatView from './components/ChatView';

const ChatScreen: FC = () => {
  const { user } = useAuthSession();
  const session = useChatSession();

  return <ChatView session={session} isAdmin={isAdminUser(user)} />;
};

export default ChatScreen;
