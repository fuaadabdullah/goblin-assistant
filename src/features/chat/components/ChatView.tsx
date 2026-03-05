import ChatHeader from './ChatHeader';
import ChatMessageList from './ChatMessageList';
import ChatComposer from './ChatComposer';
import ChatSidebar from './ChatSidebar';
import type { ChatSessionState } from '../hooks/useChatSession';
import Seo from '../../../components/Seo';

interface ChatViewProps {
  /** Chat session state + handlers. */
  session: ChatSessionState;
  /** Is the current user an admin. */
  isAdmin: boolean;
}

const ChatView = ({ session, isAdmin }: ChatViewProps) => {
  const {
    messages,
    input,
    isSending,
    totalTokens,
    totalCostUsd,
    quickPrompts,
    threads,
    isThreadsLoading,
    activeThreadId,
    inputRef,
    bottomRef,
    setInput,
    sendMessage,
    selectThread,
    handleClearChat,
    handlePromptClick,
    handleKeyDown,
    selectedProvider,
    selectedModel,
    inputEstimate,
  } = session;

  return (
    <div className="min-h-[calc(100vh-64px)] bg-bg">
      <Seo
        title="Chat"
        description="Chat with Goblin Assistant. See the model and cost as you go."
        robots="noindex,nofollow"
      />
      <div className="flex">
        <ChatSidebar
          threads={threads}
          isThreadsLoading={isThreadsLoading}
          activeThreadId={activeThreadId}
          onSelectThread={selectThread}
          onNewConversation={handleClearChat}
          isAdmin={isAdmin}
          totalTokens={totalTokens}
          messageCount={messages.length}
        />

        <main
          className="flex-1 flex flex-col bg-bg"
          id="main-content"
          tabIndex={-1}
          aria-label="Chat"
        >
          <ChatHeader isAdmin={isAdmin} onClear={handleClearChat} />
          <section className="flex-1 overflow-y-auto px-4 py-8">
            <ChatMessageList
              messages={messages}
              quickPrompts={quickPrompts}
              onPromptClick={handlePromptClick}
              bottomRef={bottomRef}
              isSending={isSending}
            />
          </section>
          <footer>
            <ChatComposer
              input={input}
              inputRef={inputRef}
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
