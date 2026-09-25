import ChatHeader from './ChatHeader';
import ChatMessageList from './ChatMessageList';
import ChatComposer from './ChatComposer';
import ChatSidebar from './ChatSidebar';
import { useCallback, useState } from 'react';
import { apiClient } from '../../../lib/api';
import type { ChatSessionState } from '../hooks/useChatSession';
import Seo from '../../../components/Seo';
import { useAuthSession } from '../../../hooks/api/useAuthSession';
import ChatPreviewPanel from './ChatPreviewPanel';
import Link from 'next/link';
import { X } from 'lucide-react';
import { Input } from '../../../components/ui';
import { useUIStore } from '../../../store/uiStore';
import { useFocusTrap } from '../../../hooks/useFocusTrap';
import { useVisualViewportHeight } from '../../../hooks/useVisualViewportHeight';
import { useTabListKeyboardNav } from '../../../hooks/useTabListKeyboardNav';

const MOBILE_CHAT_PANEL_TABS = ['conversations', 'preview'] as const;
type MobileChatPanelTab = (typeof MOBILE_CHAT_PANEL_TABS)[number];

interface ChatViewProps {
  /** Chat session state + handlers. */
  session: ChatSessionState;
  /** Is the current user an admin. */
  isAdmin: boolean;
  /** Unauthenticated guest session (via ?guest=1). */
  isGuest?: boolean;
}

const ChatView = ({ session, isAdmin, isGuest = false }: ChatViewProps) => {
  const { isAuthenticated } = useAuthSession();
  const chatSidebarOpen = useUIStore((state) => state.chatSidebarOpen);
  const setChatSidebarOpen = useUIStore((state) => state.setChatSidebarOpen);
  const chatGuestBannerDismissed = useUIStore((state) => state.chatGuestBannerDismissed);
  const dismissChatGuestBanner = useUIStore((state) => state.dismissChatGuestBanner);
  // Keeps the pinned composer above the on-screen keyboard on iOS Safari.
  useVisualViewportHeight();
  const [mobilePanelTab, setMobilePanelTab] = useState<MobileChatPanelTab>('conversations');
  const { onKeyDown: onMobilePanelTabKeyDown, registerTab: registerMobilePanelTab } =
    useTabListKeyboardNav(MOBILE_CHAT_PANEL_TABS, mobilePanelTab, setMobilePanelTab);
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
    authError,
    setInput,
    sendMessage,
    selectThread,
    handleClearChat,
    handlePromptClick,
    handleKeyDown,
    selectedProvider,
    selectedModel,
    selectedMode,
    setSelectedMode,
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

  const rateFeedback = useCallback(
    async (messageId: string, rating: 1 | -1) => {
      const msg = messages.find((m) => m.id === messageId);
      const requestId = msg?.meta?.correlation_id;
      if (!requestId) return;
      try {
        const provider = msg?.meta?.provider;
        const department = msg?.meta?.department || msg?.meta?.department_reason;
        // Use the active thread id as conversation_id for feedback context
        const conversationId = threads.find((t) => t.threadKey === activeThreadKey)?.id || '';
        await apiClient.submitRoutingFeedback({
          requestId,
          rating,
          ...(provider && { providerId: provider }),
          ...(msg?.meta?.model && { model: msg.meta.model }),
          ...(department && { department: department }),
          messageId,
          conversationId,
        });
      } catch {
        // best-effort — feedback failure is silent
      }
    },
    [messages, threads, activeThreadKey]
  );

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

  if (!isAuthenticated && !isGuest) {
    return (
      <div className="chat-viewport-min bg-bg flex items-center justify-center px-4">
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
    <div className="chat-viewport flex flex-col overflow-hidden bg-bg">
      <Seo
        title="Chat"
        description="Chat with Goblin Assistant. See the model and cost as you go."
        robots="noindex,nofollow"
      />
      <div className="relative flex flex-1 min-h-0">
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
                onKeyDown={onMobilePanelTabKeyDown}
              >
                {MOBILE_CHAT_PANEL_TABS.map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    id={`mobile-chat-tab-${tab}`}
                    role="tab"
                    aria-selected={mobilePanelTab === tab}
                    aria-controls={`mobile-chat-tabpanel-${tab}`}
                    tabIndex={mobilePanelTab === tab ? 0 : -1}
                    ref={registerMobilePanelTab(tab)}
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
              <div
                className="contents"
                role="tabpanel"
                id="mobile-chat-tabpanel-conversations"
                aria-labelledby="mobile-chat-tab-conversations"
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
                  className="h-full w-full border-0 shadow-none"
                />
              </div>
            ) : (
              <div
                className="h-full overflow-y-auto p-4"
                role="tabpanel"
                id="mobile-chat-tabpanel-preview"
                aria-labelledby="mobile-chat-tab-preview"
              >
                <ChatPreviewPanel />
              </div>
            )}
          </div>
        </div>

        {!isGuest && (
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
        )}

        <main
          className="flex-1 min-h-0 flex flex-col bg-bg"
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
          {isGuest && !chatGuestBannerDismissed && (
            <div className="shrink-0 mx-3 mt-2 flex items-center gap-2 rounded-xl border border-primary/40 bg-surface px-3 py-2 sm:mx-4 sm:mt-4 sm:gap-3 sm:px-4 sm:py-3">
              <p className="min-w-0 flex-1 truncate text-xs text-muted sm:text-sm">
                <span className="font-semibold text-primary">Guest session</span>
                <span className="hidden sm:inline"> — messages are not saved.</span>{' '}
                <Link href="/login" className="text-primary hover:underline font-medium">
                  <span>Sign in to save history</span>
                </Link>
              </p>
              <Link
                href="/login"
                className="inline-flex min-h-11 shrink-0 items-center rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-text-inverse sm:text-sm"
              >
                <span>Sign in</span>
              </Link>
              <button
                type="button"
                onClick={dismissChatGuestBanner}
                className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted hover:bg-surface-hover hover:text-text"
                aria-label="Dismiss guest notice"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          )}
          <section className="flex-1 min-h-0 overscroll-contain">
            <ChatMessageList
              messages={messages}
              quickPrompts={quickPrompts}
              onPromptClick={handlePromptClick}
              selectedMode={selectedMode}
              onModeChange={setSelectedMode}
              isSending={isSending}
              isLoading={isMessagesLoading}
              onDeleteMessage={deleteMessage}
              onCopyMessage={copyMessage}
              onRegenerateMessage={regenerateMessage}
              onRateFeedback={rateFeedback}
            />
          </section>
          <footer className="shrink-0">
            <ChatComposer
              input={input}
              inputRef={inputRef}
              authError={authError}
              isSending={isSending}
              quickPrompts={quickPrompts}
              hasMessages={messages.length > 0}
              onInputChange={setInput}
              onClear={handleClearChat}
              onSend={() => sendMessage()}
              onKeyDown={handleKeyDown}
              onPromptClick={handlePromptClick}
              onFileSelected={isGuest ? undefined : handleFileSelected}
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
