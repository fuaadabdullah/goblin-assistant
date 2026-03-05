import ChatScreen from '../features/chat/ChatScreen';

const ChatPage = () => <ChatScreen />;

// Prevent static generation - requires server-side data
export const getServerSideProps = async () => {
  return { props: {} };
};

export default ChatPage;
