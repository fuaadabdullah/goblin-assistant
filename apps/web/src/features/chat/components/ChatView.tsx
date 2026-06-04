import ChatHeader from './ChatHeader';
import ChatMessageList from './ChatMessageList';
import ChatComposer from './ChatComposer';
import ChatSidebar from './ChatSidebar';
import { useCallback, useState } from 'react';
import type { ChatSessionState } from '../hooks/useChatSession';
import Seo from '../../../components/Seo';
import { useAuthSession } from '../../../hooks/api/useAuthSession';
import ChatPreviewPanel from './ChatPreviewPanel';
import Link from 'next/link';
import { Input } from '../../../components/ui/input';
import { useUIStore } from '../../../store/uiStore';
import { useFocusTrap } from '../../../hooks/useFocusTrap';

type MobileChatPanelTab = 'conversations' | 'preview';

interface ChatViewProps {
  /** Chat session state + handlers. */
  session: ChatSessionState;
  /** Is the current user an admin. */
  isAdmin: boolean;
}

const ChatView = ({ session, isAdmin }: ChatViewProps) => {
  const { isAuthenticated } = useAuthSession();
  const chatSidebarOpen = useUIStore((state) => state.chatSidebarOpen);
  const setChatSidebarOpen = useUIStore((state) => state.setChatSidebarOpen);
  const [mobilePanelTab, setMobilePanelTab] = useState<MobileChatPanelTab>('conversations');
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
    pendingAttachments,
    isUploading,
    handleFileSelected,
    removePendingAttachment,
  } = session;

  const closeMobilePanel = useCallback(() => setChatSidebarOpen(false), [setChatSidebarOpen]);
  const mobilePanelRef = useFocusTrap(chatSidebarOpen, closeMobilePanel);
  const toggleMobilePanel = useCallback(() => {
    setChatSidebarOpen(!chatSidebarOpen);
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
        <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6 py-12">
          <div className="rounded-2xl border border-border bg-surface p-6 shadow-card">
            <ChatPreviewPanel />
          </div>

          <aside className="rounded-2xl border border-border bg-surface p-6 shadow-card">
            <h2 className="text-lg font-semibold text-text">Continue the conversation</h2>
            <p className="text-sm text-muted mt-2">pick up where the preview left off</p>

            <div className="mt-6">
              <Input placeholder="Sign in to continue this conversation..." disabled />
            </div>

            <div className="mt-4 grid gap-2">
              <Link
                href={{ pathname: '/login' }}
                className="inline-flex items-center justify-center px-4 py-2 rounded-lg bg-primary text-text-inverse font-medium"
              >
                Sign in to Goblin →
              </Link>

              <Link
                href={{ pathname: '/login', query: { mode: 'register' } }}
                className="inline-flex items-center justify-center px-4 py-2 rounded-lg border border-primary text-primary font-medium"
              >
                Create account
              </Link>
            </div>

            <div className="mt-6">
              <div className="text-sm text-muted">Features</div>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-hover text-sm">
                  Finance analysis
                </span>
                <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-hover text-sm">
                  Live code
                </span>
                <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-surface-hover text-sm">
                  Smart memory
                </span>
              </div>
            </div>
          </aside>
        </div>
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
          ref={mobilePanelRef}
          role="dialog"
          aria-label="Chat mobile panel"
          className={`fixed inset-0 z-40 lg:hidden ${
            chatSidebarOpen ? 'pointer-events-auto' : 'pointer-events-none'
          }`}
        >
          <button
            type="button"
            aria-label="Close chat panel"
            className={`absolute inset-0 bg-black/50 backdrop-blur-sm transition-opacity duration-200 ${
              chatSidebarOpen ? 'opacity-100' : 'opacity-0'
            }`}
            onClick={() => setChatSidebarOpen(false)}
          />
          <div
            id="mobile-chat-panel"
            className={`absolute inset-y-0 left-0 flex w-[88vw] max-w-sm flex-col border-r border-border bg-surface shadow-2xl transition-transform duration-200 ease-out ${
              chatSidebarOpen ? 'translate-x-0' : '-translate-x-full'
            } pt-[max(0px,env(safe-area-inset-top))]`}
          >
            <div className="border-b border-border p-3">
              <div
                className="grid grid-cols-2 gap-2 rounded-lg bg-bg p-1"
                role="tablist"
                aria-label="Chat panel sections"
              >
                {(['conversations', 'preview'] as const).map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    role="tab"
                    aria-selected={mobilePanelTab === tab}
                    onClick={() => setMobilePanelTab(tab)}
                    className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                      mobilePanelTab === tab
                        ? 'bg-primary text-text-inverse'
                        : 'text-muted hover:bg-surface-hover hover:text-text'
                    }`}
                  >
                    {tab === 'conversations' ? 'Conversations' : 'Preview'}
                  </button>
                ))}
              </div>
            </div>
            {mobilePanelTab === 'conversations' ? (
              <ChatSidebar
                threads={threads}
                isThreadsLoading={isThreadsLoading}
                activeThreadKey={activeThreadKey}
                onSelectThread={handleThreadSelect}
                onNewConversation={handleNewConversation}
                isAdmin={isAdmin}
                totalTokens={totalTokens}
                messageCount={messages.length}
                className="h-full w-full border-0 shadow-none"
              />
            ) : (
              <div className="h-full overflow-y-auto p-4">
                <ChatPreviewPanel />
              </div>
            )}
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
            showMobilePanelToggle
            onToggleMobilePanel={toggleMobilePanel}
            isMobilePanelOpen={chatSidebarOpen}
            activeMobilePanelTab={mobilePanelTab}
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
              onFileSelected={handleFileSelected}
              selectedProvider={selectedProvider}
              selectedModel={selectedModel}
              estimatedTokens={inputEstimate?.estimated_tokens}
              estimatedCostUsd={inputEstimate?.estimated_cost_usd}
              totalTokens={totalTokens}
              totalCostUsd={totalCostUsd}
              pendingAttachments={pendingAttachments}
              isUploading={isUploading}
              onRemoveAttachment={removePendingAttachment}
            />
          </footer>
        </main>
      </div>
    </div>
  );
};

export default ChatView;
