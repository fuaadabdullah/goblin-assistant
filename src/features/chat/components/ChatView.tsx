import ChatHeader from './ChatHeader';
import ChatMessageList from './ChatMessageList';
import ChatComposer from './ChatComposer';
import ChatSidebar from './ChatSidebar';
import { useEffect } from 'react';
import type { ChatSessionState } from '../hooks/useChatSession';
import Seo from '../../../components/Seo';
import { useAuthSession } from '../../../hooks/api/useAuthSession';
import AuthPrompt from '../../../components/Auth/AuthPrompt';
import { useUIStore } from '../../../store/uiStore';

interface ChatViewProps {
  /** Chat session state + handlers. */
  session: ChatSessionState;
  /** Is the current user an admin. */
  isAdmin: boolean;
}

const ChatView = ({ session, isAdmin }: ChatViewProps) => {
  const { isAuthenticated } = useAuthSession();
  const chatSidebarOpen = useUIStore((state) => state.chatSidebarOpen);
  const toggleChatSidebar = useUIStore((state) => state.toggleChatSidebar);
  const setChatSidebarOpen = useUIStore((state) => state.setChatSidebarOpen);
  const {
    messages,
    input,
    isSending,
    totalTokens,
    totalCostUsd,
    quickPrompts,
    threads,
    isThreadsLoading,
    activeThreadKey,
    inputRef,
    bottomRef,
    authError,
    setInput,
    sendMessage,
    selectThread,
    handleClearChat,
    handlePromptClick,
    handleKeyDown,
    selectedProvider,
    selectedModel,
    inputEstimate,
    isMessagesLoading,
    deleteMessage,
    copyMessage,
    regenerateMessage,
  } = session;

  useEffect(() => {
    if (!chatSidebarOpen) return undefined;

    const onEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setChatSidebarOpen(false);
      }
    };

    window.addEventListener('keydown', onEscape);
    document.body.style.overflow = 'hidden';

    return () => {
      window.removeEventListener('keydown', onEscape);
      document.body.style.overflow = '';
    };
  }, [chatSidebarOpen, setChatSidebarOpen]);

  const handleThreadSelect = (threadKey: string) => {
    selectThread(threadKey);
    setChatSidebarOpen(false);
  };

  const handleNewConversation = () => {
    handleClearChat();
    setChatSidebarOpen(false);
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-[calc(100vh-64px)] bg-bg flex items-center justify-center px-4">
        <Seo
          title="Chat - Sign In Required"
          description="Sign in to chat with Goblin Assistant"
          robots="noindex,nofollow"
        />
        <AuthPrompt
          title="Sign in to start chatting"
          message="Create an account or sign in to start chatting with Goblin Assistant."
          mode="inline"
        />
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-64px)] bg-bg">
      <Seo
        title="Chat"
        description="Chat with Goblin Assistant. See the model and cost as you go."
        robots="noindex,nofollow"
      />
      <div className="relative flex">
        <div
          className={`fixed inset-0 z-40 lg:hidden ${
            chatSidebarOpen ? 'pointer-events-auto' : 'pointer-events-none'
          }`}
          aria-hidden={!chatSidebarOpen}
        >
          <button
            type="button"
            aria-label="Close conversations drawer"
            className={`absolute inset-0 bg-black/50 transition-opacity duration-200 ${
              chatSidebarOpen ? 'opacity-100' : 'opacity-0'
            }`}
            onClick={() => setChatSidebarOpen(false)}
          />
          <div
            id="mobile-chat-sidebar"
            className={`absolute inset-y-0 left-0 transition-transform duration-200 ease-out ${
              chatSidebarOpen ? 'translate-x-0' : '-translate-x-full'
            }`}
          >
            <ChatSidebar
              threads={threads}
              isThreadsLoading={isThreadsLoading}
              activeThreadKey={activeThreadKey}
              onSelectThread={handleThreadSelect}
              onNewConversation={handleNewConversation}
              isAdmin={isAdmin}
              totalTokens={totalTokens}
              messageCount={messages.length}
              className="h-full w-[85vw] max-w-sm shadow-2xl"
            />
          </div>
        </div>

        <ChatSidebar
          threads={threads}
          isThreadsLoading={isThreadsLoading}
          activeThreadKey={activeThreadKey}
          onSelectThread={handleThreadSelect}
          onNewConversation={handleNewConversation}
          isAdmin={isAdmin}
          totalTokens={totalTokens}
          messageCount={messages.length}
          className="hidden lg:flex sticky top-0 h-screen"
        />

        <main
          className="flex-1 flex flex-col bg-bg"
          id="main-content"
          tabIndex={-1}
          aria-label="Chat"
        >
          <ChatHeader
            isAdmin={isAdmin}
            onClear={handleClearChat}
            showSidebarToggle
            onToggleSidebar={toggleChatSidebar}
            isSidebarOpen={chatSidebarOpen}
          />
          <section className="flex-1 overflow-y-auto px-4 py-8">
            <ChatMessageList
              messages={messages}
              quickPrompts={quickPrompts}
              onPromptClick={handlePromptClick}
              bottomRef={bottomRef}
              isSending={isSending}
              isLoading={isMessagesLoading}
              onDeleteMessage={deleteMessage}
              onCopyMessage={copyMessage}
              onRegenerateMessage={regenerateMessage}
            />
          </section>
          <footer>
            <ChatComposer
              input={input}
              inputRef={inputRef}
              authError={authError}
              isSending={isSending}
              quickPrompts={quickPrompts}
              onInputChange={setInput}
              onClear={handleClearChat}
              onSend={() => sendMessage()}
              onKeyDown={handleKeyDown}
              onPromptClick={handlePromptClick}
              selectedProvider={selectedProvider}
              selectedModel={selectedModel}
              estimatedTokens={inputEstimate?.estimated_tokens}
              estimatedCostUsd={inputEstimate?.estimated_cost_usd}
              totalTokens={totalTokens}
              totalCostUsd={totalCostUsd}
            />
          </footer>
        </main>
      </div>
    </div>
  );
};

export default ChatView;
