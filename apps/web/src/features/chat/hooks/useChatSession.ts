import type { RefObject } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { chatClient } from '../api';
import type { ChatMessage, ChatThread, QuickPrompt } from '../types';
import { useChatThreads } from './useChatThreads';
import { readChatMessages, buildThreadKey } from '../../../lib/chat-history';
import { queryKeys } from '../../../lib/query-keys';
import { useMessages, type MessagesState } from './useMessages';
import { useUIState, type UIState } from './useUIState';
import { useThreadSelection, type ThreadSelectionState } from './useThreadSelection';
import { useInputEstimates, type InputEstimatesState } from './useInputEstimates';
import { useQuickActions, type QuickActionsState } from './useQuickActions';
import type { TextCostEstimate } from '../../../lib/cost-estimate';

export interface PendingAttachment {
  file_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
}

export interface ChatSessionState {
  messages: ChatMessage[];
  input: string;
  isSending: boolean;
  isMessagesLoading: boolean;
  isLoadingOlderMessages: boolean;
  hasMoreMessages: boolean;
  totalTokens: number;
  totalCostUsd: number;
  quickPrompts: QuickPrompt[];
  threads: ChatThread[];
  isThreadsLoading: boolean;
  activeThreadKey: string | null;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  bottomRef: RefObject<HTMLDivElement | null>;
  selectedProvider?: string | undefined;
  selectedModel?: string | undefined;
  inputEstimate: TextCostEstimate | null;
  authError: boolean;
  pendingAttachments: PendingAttachment[];
  isUploading: boolean;
  setInput: (value: string) => void;
  sendMessage: (messageOverride?: string) => Promise<void>;
  selectThread: (threadKey: string) => void;
  handleClearChat: () => void;
  handlePromptClick: (prompt: string) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  deleteMessage: (messageId: string) => void;
  copyMessage: (content: string) => Promise<void>;
  regenerateMessage: (messageId: string) => Promise<void>;
  handleFileSelected: (files: FileList) => void;
  removePendingAttachment: (fileId: string) => void;
  loadOlderMessages: () => Promise<void>;
}

/**
 * Main chat session hook - orchestrates focused hooks for messages, UI, threads, estimates, and quick actions
 *
 * This hook composes:
 * - useMessages: message operations (send, delete, regenerate, load older)
 * - useUIState: input, file uploads, keyboard handlers
 * - useThreadSelection: active thread management
 * - useInputEstimates: token/cost estimates for input
 * - useQuickActions: quick prompts and provider selection
 * - useChatThreads: thread list management
 */
export const useChatSession = (): ChatSessionState => {
  const searchParams = useSearchParams();
  const promptParam = searchParams.get('prompt');
  const hasHydratedRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // Thread management
  const {
    threads,
    isLoading: isThreadsLoading,
    upsertThread,
    removeThread,
    invalidateThreads,
  } = useChatThreads();

  // Thread selection state
  const [activeThreadKey, setActiveThreadKey] = useState<string | null>(null);
  const threadSelection = useThreadSelection(activeThreadKey, setActiveThreadKey);

  // Quick actions and provider selection
  const quickActionsState = useQuickActions();

  // Backend conversation query
  const backendConversationQuery = useQuery({
    queryKey: threadSelection.activeBackendThreadId
      ? queryKeys.chatConversation(threadSelection.activeBackendThreadId)
      : ['chat', 'conversation', 'inactive'],
    queryFn: async () => {
      if (!threadSelection.activeBackendThreadId) {
        throw new Error('No active backend thread id');
      }
      return chatClient.getConversation(threadSelection.activeBackendThreadId, {
        offset: 0,
        limit: 50,
      });
    },
    enabled: Boolean(threadSelection.activeBackendThreadId),
    staleTime: 30_000,
  });

  // UI state (input, file uploads, keyboard handlers)
  const uiState = useUIState({
    onSendMessage: async () => {
      await messagesState.sendMessage();
    },
    onClearMessages: () => {
      messagesState.setMessages([]);
    },
  });

  // Messages and message operations
  const messagesState = useMessages({
    input: uiState.input,
    activeThread: threadSelection.activeThread,
    activeBackendThreadId: threadSelection.activeBackendThreadId,
    selectedProvider: quickActionsState.selectedProvider,
    selectedModel: quickActionsState.selectedModel,
    pendingAttachments: uiState.pendingAttachments,
    onThreadUpdated: upsertThread,
    onThreadRemoved: removeThread,
    onThreadsInvalidated: invalidateThreads,
    backendConversationQuery,
  });

  // Input estimation (tokens and costs)
  const estimatesState = useInputEstimates({
    input: uiState.input,
    conversationId: threadSelection.activeBackendThreadId,
    selectedProvider: quickActionsState.selectedProvider,
    selectedModel: quickActionsState.selectedModel,
  });

  // Scroll to bottom on new messages
  const prefersReducedMotion = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
  }, [messagesState.messages, prefersReducedMotion]);

  // Prefill input from URL query param
  useEffect(() => {
    if (typeof promptParam === 'string' && promptParam.trim().length > 0) {
      uiState.setInput(promptParam);
      uiState.inputRef.current?.focus();
    }
  }, [promptParam]);

  // Initialize active thread and load messages
  useEffect(() => {
    if (!hasHydratedRef.current) {
      if (isThreadsLoading) {
        return;
      }
      hasHydratedRef.current = true;
      if (threads.length > 0 && !activeThreadKey) {
        setActiveThreadKey(threads[0]!.threadKey);
      }
      return;
    }

    if (!activeThreadKey) {
      return;
    }

    if (!threadSelection.activeThread) {
      messagesState.setMessages([]);
      // If threads are available (e.g. after legacy→backend promotion), select the first one.
      // Otherwise clear the selection entirely.
      setActiveThreadKey(threads.length > 0 ? threads[0]!.threadKey : null);
      return;
    }

    uiState.setInput('');

    if (threadSelection.activeThread.source === 'legacy-local') {
      messagesState.setMessages(readChatMessages(threadSelection.activeThread.id));
      return;
    }

    if (
      threadSelection.activeThread.source === 'backend' &&
      backendConversationQuery.data?.conversationId === threadSelection.activeThread.id
    ) {
      messagesState.setMessages(backendConversationQuery.data.messages);
      const paginationInfo = backendConversationQuery.data?.pagination;
      if (paginationInfo) {
        // Update pagination state in messagesState
      }
    }
  }, [
    threadSelection.activeThread,
    activeThreadKey,
    backendConversationQuery.data,
    isThreadsLoading,
    threads,
  ]);

  // Wrap sendMessage to clear attachments after sending
  const sendMessageWithCleanup = useCallback(
    async (messageOverride?: string) => {
      await messagesState.sendMessage(messageOverride);
      uiState.inputRef.current?.focus();
    },
    [messagesState, uiState]
  );

  // Wrap selectThread to focus input
  const selectThreadWithFocus = useCallback(
    (threadKey: string) => {
      threadSelection.selectThread(threadKey);
      uiState.inputRef.current?.focus();
    },
    [threadSelection, uiState]
  );

  // Wrap handleClearChat to clear attachments
  const handleClearChatWithCleanup = useCallback(() => {
    uiState.handleClearChat();
    messagesState.setMessages([]);
    setActiveThreadKey(null);
  }, [uiState, messagesState]);

  return {
    // Messages state
    messages: messagesState.messages,
    isSending: messagesState.isSending,
    isMessagesLoading: messagesState.isMessagesLoading,
    isLoadingOlderMessages: messagesState.isLoadingOlderMessages,
    hasMoreMessages: messagesState.hasMoreMessages,
    totalTokens: messagesState.totalTokens,
    totalCostUsd: messagesState.totalCostUsd,

    // UI state
    input: uiState.input,
    setInput: uiState.setInput,
    authError: uiState.authError,
    pendingAttachments: uiState.pendingAttachments,
    isUploading: uiState.isUploading,
    inputRef: uiState.inputRef,
    bottomRef,

    // Thread state
    threads: threadSelection.threads,
    isThreadsLoading: threadSelection.isThreadsLoading,
    activeThreadKey: threadSelection.activeThreadKey,

    // Estimates state
    inputEstimate: estimatesState.inputEstimate,

    // Quick actions state
    quickPrompts: quickActionsState.quickPrompts,
    selectedProvider: quickActionsState.selectedProvider,
    selectedModel: quickActionsState.selectedModel,

    // Message handlers
    sendMessage: sendMessageWithCleanup,
    deleteMessage: messagesState.deleteMessage,
    copyMessage: messagesState.copyMessage,
    regenerateMessage: messagesState.regenerateMessage,
    loadOlderMessages: messagesState.loadOlderMessages,

    // UI handlers
    selectThread: selectThreadWithFocus,
    handleClearChat: handleClearChatWithCleanup,
    handlePromptClick: uiState.handlePromptClick,
    handleKeyDown: uiState.handleKeyDown,
    handleFileSelected: uiState.handleFileSelected,
    removePendingAttachment: uiState.removePendingAttachment,
  };
};
