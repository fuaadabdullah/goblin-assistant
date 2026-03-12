import type { KeyboardEvent, RefObject } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { chatClient } from '../api';
import { toUiError } from '../../../lib/ui-error';
import type { ChatMessage, ChatThread, QuickPrompt } from '../types';
import { useChatThreads } from './useChatThreads';
import { buildThreadKey, readChatMessages } from '../../../lib/chat-history';
import { queryKeys } from '../../../lib/query-keys';
import { CHAT_QUICK_PROMPTS } from '../../../content/brand';
import { estimateFromText, type TextCostEstimate } from '../../../lib/cost-estimate';
import { computeCostUsd } from '../../../lib/llm-rates';
import { useProvider } from '../../../contexts/ProviderContext';
import { isAuthenticated } from '../../../utils/auth-session';
import { apiClient } from '@/api';
import { devError, devLog } from '@/utils/dev-log';

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
  totalTokens: number;
  totalCostUsd: number;
  quickPrompts: QuickPrompt[];
  threads: ChatThread[];
  isThreadsLoading: boolean;
  activeThreadKey: string | null;
  inputRef: RefObject<HTMLTextAreaElement>;
  bottomRef: RefObject<HTMLDivElement>;
  selectedProvider?: string;
  selectedModel?: string;
  inputEstimate: TextCostEstimate | null;
    authError: boolean;
  pendingAttachments: PendingAttachment[];
  isUploading: boolean;
  setInput: (value: string) => void;
  sendMessage: (messageOverride?: string) => Promise<void>;
  selectThread: (threadKey: string) => void;
  handleClearChat: () => void;
  handlePromptClick: (prompt: string) => void;
  handleKeyDown: (e: KeyboardEvent<HTMLTextAreaElement>) => void;
  deleteMessage: (messageId: string) => void;
  copyMessage: (content: string) => Promise<void>;
  regenerateMessage: (messageId: string) => Promise<void>;
  handleFileSelected: (files: FileList) => void;
  removePendingAttachment: (fileId: string) => void;
}

const createMessageId = (): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
};

const calculateTotals = (items: ChatMessage[]) => {
  const totals = items.reduce(
    (acc, message) => {
      const usageTokens = message.meta?.usage?.total_tokens;
      const inputTokens = message.meta?.usage?.input_tokens || 0;
      const outputTokens = message.meta?.usage?.output_tokens || 0;
      const tokens = typeof usageTokens === 'number' ? usageTokens : inputTokens + outputTokens;

      if (typeof tokens === 'number' && Number.isFinite(tokens)) {
        acc.totalTokens += tokens;
      }
      if (typeof message.meta?.cost_usd === 'number' && Number.isFinite(message.meta.cost_usd)) {
        acc.totalCostUsd += message.meta.cost_usd;
      }
      return acc;
    },
    { totalTokens: 0, totalCostUsd: 0 }
  );

  return {
    totalTokens: totals.totalTokens,
    totalCostUsd: Number(totals.totalCostUsd.toFixed(6)),
  };
};

export const useChatSession = (): ChatSessionState => {
  const queryClient = useQueryClient();
  const {
    threads,
    isLoading: isThreadsLoading,
    upsertThread,
    removeThread,
    invalidateThreads,
  } = useChatThreads();
  const { selectedProvider, selectedModel } = useProvider();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [totalTokens, setTotalTokens] = useState(0);
  const [totalCostUsd, setTotalCostUsd] = useState(0);
  const [activeThreadKey, setActiveThreadKey] = useState<string | null>(null);
    const [authError, setAuthError] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const hasHydratedRef = useRef(false);

  const inputEstimate = useMemo(() => {
    const est = estimateFromText(input);
    return est.estimated_tokens > 0 ? est : null;
  }, [input]);

  const quickPrompts = useMemo<QuickPrompt[]>(
    () => CHAT_QUICK_PROMPTS.map(item => ({ label: item.label, prompt: item.prompt })),
    []
  );

  const prefersReducedMotion = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false;
  }, []);

  const activeThread = useMemo(
    () => threads.find((thread: ChatThread) => thread.threadKey === activeThreadKey) ?? null,
    [activeThreadKey, threads]
  );

  const activeBackendThreadId = useMemo(
    () => (activeThread?.source === 'backend' ? activeThread.id : null),
    [activeThread],
  );

  const backendConversationQuery = useQuery({
    queryKey: activeBackendThreadId
      ? queryKeys.chatConversation(activeBackendThreadId)
      : ['chat', 'conversation', 'inactive'],
    queryFn: async () => {
      if (!activeBackendThreadId) {
        throw new Error('No active backend thread id');
      }
      return chatClient.getConversation(activeBackendThreadId);
    },
    enabled: Boolean(activeBackendThreadId),
    staleTime: 30_000,
  });

  const isMessagesLoading =
    activeThread?.source === 'backend' && !backendConversationQuery.data
      ? backendConversationQuery.isLoading || backendConversationQuery.isFetching
      : false;

  const applyMessages = useCallback((nextMessages: ChatMessage[]) => {
    setMessages(nextMessages);
    const totals = calculateTotals(nextMessages);
    setTotalTokens(totals.totalTokens);
    setTotalCostUsd(totals.totalCostUsd);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
  }, [messages, prefersReducedMotion]);

  useEffect(() => {
    if (!hasHydratedRef.current) {
      if (isThreadsLoading) {
        return;
      }
      hasHydratedRef.current = true;
      if (threads.length > 0 && !activeThreadKey) {
        setActiveThreadKey(threads[0].threadKey);
      }
      return;
    }

    if (!activeThreadKey) {
      return;
    }

    if (!activeThread) {
      applyMessages([]);
      setActiveThreadKey(null);
      return;
    }

    setInput('');

    if (activeThread.source === 'legacy-local') {
      applyMessages(readChatMessages(activeThread.id));
      return;
    }

    if (
      activeThread.source === 'backend' &&
      backendConversationQuery.data?.conversationId === activeThread.id
    ) {
      applyMessages(backendConversationQuery.data.messages);
    }
  }, [
    activeThread,
    activeThreadKey,
    applyMessages,
    backendConversationQuery.data,
    isThreadsLoading,
    threads,
  ]);

  const selectThread = useCallback((threadKey: string) => {
    setActiveThreadKey(threadKey);
    inputRef.current?.focus();
  }, []);

  const sendMessage = useCallback(
    async (messageOverride?: string) => {
      const content = (messageOverride ?? input).trim();
      if (!content || isSending || isMessagesLoading) return;

      setIsSending(true);

      const nowIso = new Date().toISOString();
      const estimate = estimateFromText(content);
      const userMsg: ChatMessage = {
        id: createMessageId(),
        createdAt: nowIso,
        role: 'user',
        content,
        meta: {
          estimated_tokens: estimate.estimated_tokens,
          estimated_cost_usd: estimate.estimated_cost_usd,
          ...(pendingAttachments.length > 0
            ? { attachments: pendingAttachments.map((a) => ({
                id: a.file_id,
                filename: a.filename,
                mime_type: a.mime_type,
                size_bytes: a.size_bytes,
              })) }
            : {}),
        },
      };
      const previousMessages = messages;
      const updatedMessages = [...previousMessages, userMsg];
      setMessages(updatedMessages);
      setInput('');

      try {
        // Guest fallback: if user is not authenticated, use the
        // unauthenticated /api/generate proxy instead of conversations API.
        const isAuthed = isAuthenticated();

        if (!isAuthed) {
          const response = await apiClient.chatCompletion(updatedMessages, selectedModel || undefined);
          const text = typeof response === 'string' ? response : String(response ?? 'No response');
          const assistantMsg: ChatMessage = {
            id: createMessageId(),
            createdAt: new Date().toISOString(),
            role: 'assistant',
            content: text,
          };
          applyMessages([...updatedMessages, assistantMsg]);
          setIsSending(false);
          inputRef.current?.focus();
          return;
        }

        let conversationId = activeThread?.source === 'backend' ? activeThread.id : null;
        let createdAt: string | undefined;
        let pendingThreadTitle = content.slice(0, 48) || 'New chat';
        let shouldPromoteLegacy = false;

        if (!conversationId && activeThread?.source === 'legacy-local') {
          const created = await chatClient.createConversation({
            title: activeThread.title || pendingThreadTitle,
          });
          conversationId = created.conversationId;
          createdAt = created.createdAt;
          pendingThreadTitle = created.title ?? activeThread.title ?? pendingThreadTitle;
          await chatClient.importConversationMessages(conversationId, previousMessages);
          shouldPromoteLegacy = true;
        }

        if (!conversationId) {
          const created = await chatClient.createConversation({
            title: pendingThreadTitle,
          });
          conversationId = created.conversationId;
          createdAt = created.createdAt;
          pendingThreadTitle = created.title ?? pendingThreadTitle;
        }

        if (!conversationId) {
          throw new Error('Conversation ID unavailable.');
        }

        const result = await chatClient.sendMessage({
          conversationId,
          prompt: content,
          model: selectedModel || undefined,
          provider: selectedProvider || undefined,
          attachment_ids: pendingAttachments.length > 0
            ? pendingAttachments.map((a) => a.file_id)
            : undefined,
        });

        // Clear pending attachments after successful send
        setPendingAttachments([]);

        const rawCost = typeof result?.cost_usd === 'number' ? result.cost_usd : undefined;
        const fallbackCost =
          rawCost !== undefined
            ? { cost_usd: rawCost, approx: false, source: 'backend' as const }
            : computeCostUsd(result?.usage, result?.provider, result?.model);

        const assistantMsg: ChatMessage = {
          id: result?.messageId || createMessageId(),
          createdAt: result?.createdAt || new Date().toISOString(),
          role: 'assistant',
          content: result?.content || 'No response',
          meta: {
            provider: result?.provider,
            model: result?.model,
            usage: result?.usage,
            cost_usd: fallbackCost.cost_usd,
            cost_is_approx: fallbackCost.approx,
            correlation_id: result?.correlation_id,
            visualizations: result?.visualizations,
          },
        };

        const nextMessages = [...updatedMessages, assistantMsg];
        applyMessages(nextMessages);

        queryClient.setQueryData(
          queryKeys.chatConversation(conversationId),
          (current:
            | {
                conversationId: string;
                title: string;
                createdAt: string;
                updatedAt: string;
                messages: ChatMessage[];
              }
            | undefined) => {
            if (!current) {
              return {
                conversationId,
                title: pendingThreadTitle,
                createdAt: createdAt ?? assistantMsg.createdAt,
                updatedAt: assistantMsg.createdAt,
                messages: nextMessages,
              };
            }

            return {
              ...current,
              updatedAt: assistantMsg.createdAt,
              messages: nextMessages,
            };
          },
        );

        const backendThreadKey = buildThreadKey('backend', conversationId);
        upsertThread({
          id: conversationId,
          source: 'backend',
          title: pendingThreadTitle,
          snippet: assistantMsg.content,
          createdAt,
          updatedAt: assistantMsg.createdAt,
        });
        setActiveThreadKey(backendThreadKey);

        if (shouldPromoteLegacy && activeThread) {
          removeThread(activeThread);
        }

        void invalidateThreads();
      } catch (err: unknown) {
        const uiError = toUiError(err, {
          code: 'CHAT_SEND_FAILED',
          userMessage: 'Sorry, we could not send that message right now.',
        });
        
        // Check if this is an authentication error
        if (uiError.code === 'AUTHENTICATION_REQUIRED') {
          setAuthError(true);
          // Don't show error message in chat for auth errors
        } else {
          const assistantMsg: ChatMessage = {
            id: `msg-error-${Date.now()}`,
            createdAt: new Date().toISOString(),
            role: 'assistant',
            content: uiError.userMessage,
          };
          applyMessages([...updatedMessages, assistantMsg]);
        }
      } finally {
        setIsSending(false);
        inputRef.current?.focus();
      }
    },
    [
      activeThread,
      applyMessages,
      input,
      invalidateThreads,
      isMessagesLoading,
      isSending,
      messages,
      removeThread,
      selectedModel,
      selectedProvider,
      queryClient,
      upsertThread,
    ]
  );

  const handleClearChat = useCallback(() => {
    applyMessages([]);
    setInput('');
    setPendingAttachments([]);
    setActiveThreadKey(null);
    inputRef.current?.focus();
  }, [applyMessages]);

  const handleFileSelected = useCallback((files: FileList) => {
    setIsUploading(true);
    const uploads = Array.from(files).map(async (file) => {
      try {
        const result = await apiClient.uploadFile(file);
        return result as PendingAttachment;
      } catch (err) {
        devError('file_upload_failed', err);
        return null;
      }
    });
    void Promise.all(uploads).then((results) => {
      const successful = results.filter((r): r is PendingAttachment => r !== null);
      if (successful.length > 0) {
        setPendingAttachments((prev) => [...prev, ...successful]);
      }
      setIsUploading(false);
    });
  }, []);

  const removePendingAttachment = useCallback((fileId: string) => {
    setPendingAttachments((prev) => prev.filter((a) => a.file_id !== fileId));
  }, []);

  const handlePromptClick = useCallback((prompt: string) => {
    setInput(prompt);
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        void sendMessage();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        void sendMessage();
      }
    },
    [sendMessage]
  );

  const deleteMessage = useCallback(
    (messageId: string) => {
      const filteredMessages = messages.filter((msg) => msg.id !== messageId);
      applyMessages(filteredMessages);
    },
    [messages, applyMessages]
  );

  const copyMessage = useCallback(async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      // Show toast feedback (integration with toast system if available)
      devLog('Message copied to clipboard');
    } catch (err) {
      devError('Failed to copy message:', err);
    }
  }, []);

  const regenerateMessage = useCallback(
    async (messageId: string) => {
      if (isSending) return;

      // Find the assistant message to regenerate
      const messageIndex = messages.findIndex((msg) => msg.id === messageId);
      if (messageIndex === -1) return;

      const messageToRegenerate = messages[messageIndex];
      if (messageToRegenerate.role !== 'assistant') return;

      // Find the previous user message
      const userMessageIndex = [...messages]
        .slice(0, messageIndex)
        .reverse()
        .findIndex((msg) => msg.role === 'user');

      if (userMessageIndex === -1) return;

      const userMessage = messages[messageIndex - userMessageIndex - 1];
      if (userMessage.role !== 'user') return;

      // Remove the assistant message and any subsequent messages
      const messagesUpToRegeneration = messages.slice(0, messageIndex);
      setMessages(messagesUpToRegeneration);
      setIsSending(true);

      try {
        // Check if user is authenticated
        const isAuthed = isAuthenticated();

        if (!isAuthed) {
          // Guest mode: use /api/generate
          const response = await apiClient.chatCompletion(messagesUpToRegeneration, selectedModel || undefined);
          const text = typeof response === 'string' ? response : String(response ?? 'No response');
          const assistantMsg: ChatMessage = {
            id: createMessageId(),
            createdAt: new Date().toISOString(),
            role: 'assistant',
            content: text,
          };
          applyMessages([...messagesUpToRegeneration, assistantMsg]);
        } else {
          // Authenticated mode: use conversations API
          const conversationId = activeThread?.source === 'backend' ? activeThread.id : null;
          
          if (!conversationId) {
            throw new Error('Cannot regenerate message without a conversation');
          }

          const result = await chatClient.sendMessage({
            conversationId,
            prompt: userMessage.content,
            model: selectedModel || undefined,
            provider: selectedProvider || undefined,
          });

          const rawCost = typeof result?.cost_usd === 'number' ? result.cost_usd : undefined;
          const fallbackCost =
            rawCost !== undefined
              ? { cost_usd: rawCost, approx: false, source: 'backend' as const }
              : computeCostUsd(result?.usage, result?.provider, result?.model);

          const assistantMsg: ChatMessage = {
            id: result?.messageId || createMessageId(),
            createdAt: result?.createdAt || new Date().toISOString(),
            role: 'assistant',
            content: result?.content || 'No response',
            meta: {
              provider: result?.provider,
              model: result?.model,
              usage: result?.usage,
              cost_usd: fallbackCost.cost_usd,
              cost_is_approx: fallbackCost.approx,
              correlation_id: result?.correlation_id,
              visualizations: result?.visualizations,
            },
          };

          applyMessages([...messagesUpToRegeneration, assistantMsg]);
        }
      } catch (error) {
        devError('Failed to regenerate message:', error);
        // Restore messages on error
        setMessages(messages);
      } finally {
        setIsSending(false);
        inputRef.current?.focus();
      }
    },
    [messages, isSending, activeThread, selectedModel, selectedProvider, applyMessages]
  );

  return {
    messages,
    input,
    isSending,
    isMessagesLoading,
    totalTokens,
    totalCostUsd,
    quickPrompts,
    threads,
    isThreadsLoading,
    activeThreadKey,
    inputRef,
    bottomRef,
    selectedProvider: selectedProvider || undefined,
    selectedModel: selectedModel || undefined,
    inputEstimate,
      authError,
    pendingAttachments,
    isUploading,
    setInput,
    sendMessage,
    selectThread,
    handleClearChat,
    handlePromptClick,
    handleKeyDown,
    deleteMessage,
    copyMessage,
    regenerateMessage,
    handleFileSelected,
    removePendingAttachment,
  };
};
