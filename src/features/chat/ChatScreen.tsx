import type { FC } from 'react';
import { useAuthStore } from '../../store/authStore';
import { isAdminUser } from '../../utils/access';
import { useChatSession } from './hooks/useChatSession';
import ChatView from './components/ChatView';

const ChatScreen: FC = () => {
  const user = useAuthStore(state => state.user);
  const session = useChatSession();

  return <ChatView session={session} isAdmin={isAdminUser(user)} />;
};

export default ChatScreen;
