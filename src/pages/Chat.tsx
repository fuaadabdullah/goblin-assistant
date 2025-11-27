import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ChatInterface } from '../components/ChatInterface';

const qc = new QueryClient();

export const Chat: React.FC = () => {
  const demoMode = new URLSearchParams(window.location.search).get('demo') === 'true';

  return (
    <QueryClientProvider client={qc}>
      <ChatInterface demoMode={demoMode} />
    </QueryClientProvider>
  );
};
