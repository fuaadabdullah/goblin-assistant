import type { KeyboardEvent, RefObject } from 'react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { chatClient } from '../api';
import { toUiError } from '../../../lib/ui-error';
import type { ChatMessage, ChatThread, QuickPrompt } from '../types';
import type { ChatMessageMeta, ChatUsage } from '../../../domain/chat';
import { useChatThreads } from './useChatThreads';
import { buildThreadKey, readChatMessages } from '../../../lib/chat-history';
import { queryKeys } from '../../../lib/query-keys';
import { CHAT_QUICK_PROMPTS } from '../../../content/brand';
import { estimateFromText, type TextCostEstimate } from '../../../lib/cost-estimate';
import { computeCostUsd } from '../../../lib/llm-rates';
import { useProvider } from '../../../contexts/ProviderContext';
import { useToast } from '../../../contexts/ToastContext';
import { isAuthenticated } from '../../../utils/auth-session';
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
  isLoadingOlderMessages: boolean;
  hasMoreMessages: boolean;
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
  loadOlderMessages: () => Promise<void>;
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

const mapAttachments = (attachments: PendingAttachment[]) =>
  attachments.map((attachment) => ({
    id: attachment.file_id,
    filename: attachment.filename,
    mime_type: attachment.mime_type,
    size_bytes: attachment.size_bytes,
  }));

const createAssistantMessage = (
  response: {
    messageId?: string;
    createdAt?: string;
    content?: string;
    provider?: string;
    model?: string;
    usage?: ChatUsage;
    cost_usd?: number;
    correlation_id?: string;
    visualizations?: ChatMessageMeta['visualizations'];
  },
): ChatMessage => {
  const rawCost = typeof response.cost_usd === 'number' ? response.cost_usd : undefined;
  const resolvedCost =
    rawCost !== undefined
      ? { cost_usd: rawCost, approx: false }
      : computeCostUsd(response.usage, response.provider, response.model);

  return {
    id: response.messageId || createMessageId(),
    createdAt: response.createdAt || new Date().toISOString(),
    role: 'assistant',
    content: response.content || 'No response',
    meta: {
      provider: response.provider,
      model: response.model,
      usage: response.usage,
      cost_usd: resolvedCost.cost_usd,
      cost_is_approx: resolvedCost.approx,
      correlation_id: response.correlation_id,
      visualizations: response.visualizations,
    },
  };
};

export const useChatSession = (): ChatSessionState => {
  const { showError, showInfo, showSuccess } = useToast();
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
  const [isLoadingOlderMessages, setIsLoadingOlderMessages] = useState(false);
  const [hasMoreMessages, setHasMoreMessages] = useState(true);
  const [messageOffset, setMessageOffset] = useState(0);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const hasHydratedRef = useRef(false);
  const router = useRouter();

  const localInputEstimate = useMemo(() => {
    const est = estimateFromText(input);
    return est.estimated_tokens > 0 ? est : null;
  }, [input]);

  const [serverInputEstimate, setServerInputEstimate] = useState<TextCostEstimate | null>(null);

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

  // Server-side estimate: more accurate (includes assembled context layers,
  // system prompt, conversation history) than the client-side char heuristic.
  // Only fetched for long inputs to keep backend traffic reasonable.
  useEffect(() => {
    if (input.length <= 200) {
      setServerInputEstimate(null);
      return;
    }
    let cancelled = false;
    const handle = setTimeout(() => {
      chatClient
        .estimateTokens({
          message: input,
          conversationId: activeBackendThreadId ?? undefined,
          provider: selectedProvider,
          model: selectedModel,
        })
        .then((est) => {
          if (cancelled) return;
          setServerInputEstimate({
            estimated_tokens: est.input_tokens + est.estimated_output_tokens,
            estimated_cost_usd: est.estimated_cost_usd,
          });
        })
        .catch((err) => {
          if (cancelled) return;
          devLog('chat.estimate_tokens_failed', { error: String(err) });
          setServerInputEstimate(null);
        });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
  }, [input, activeBackendThreadId, selectedProvider, selectedModel]);

  const inputEstimate = serverInputEstimate ?? localInputEstimate;

  const backendConversationQuery = useQuery({
    queryKey: activeBackendThreadId
      ? queryKeys.chatConversation(activeBackendThreadId)
      : ['chat', 'conversation', 'inactive'],
    queryFn: async () => {
      if (!activeBackendThreadId) {
        throw new Error('No active backend thread id');
      }
      // Initially load the first 50 messages
      return chatClient.getConversation(activeBackendThreadId, { offset: 0, limit: 50 });
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

  // Prefill input from URL query param ?prompt=... when present
  useEffect(() => {
    if (!router.isReady) return;
    const q = router.query.prompt;
    const prompt = Array.isArray(q) ? q[0] : q;
    if (typeof prompt === 'string' && prompt.trim().length > 0) {
      setInput(prompt);
      inputRef.current?.focus();
    }
  }, [router.isReady, router.query.prompt]);

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
      // Track pagination state
      const paginationInfo = backendConversationQuery.data?.pagination;
      if (paginationInfo) {
        setHasMoreMessages(paginationInfo.has_more ?? false);
        setMessageOffset(paginationInfo.offset ?? 0);
      } else {
        setHasMoreMessages(false);
        setMessageOffset(0);
      }
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
          ...(pendingAttachments.length > 0 ? { attachments: mapAttachments(pendingAttachments) } : {}),
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
          const response = await chatClient.chatCompletion(updatedMessages, selectedModel || undefined);
          const text = typeof response === 'string' ? response : String(response ?? 'No response');
          const assistantMsg: ChatMessage = {
            id: createMessageId(),
            createdAt: new Date().toISOString(),
            role: 'assistant',
            content: text,
          };
          applyMessages([...updatedMessages, assistantMsg]);
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
        const assistantMsg = createAssistantMessage(result ?? {});

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
          showInfo('Sign in required', 'Sign in to continue this conversation.');
          // Don't show error message in chat for auth errors
        } else {
          const assistantMsg: ChatMessage = {
            id: `msg-error-${Date.now()}`,
            createdAt: new Date().toISOString(),
            role: 'assistant',
            content: uiError.userMessage,
          };
          applyMessages([...updatedMessages, assistantMsg]);
          showError('Message failed', uiError.userMessage);
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
      pendingAttachments,
      removeThread,
      selectedModel,
      selectedProvider,
      showError,
      showInfo,
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
    showInfo('Uploading attachments', `Preparing ${files.length} file${files.length === 1 ? '' : 's'}.`);
    const uploads = Array.from(files).map(async (file) => {
      try {
        const result = await chatClient.uploadFile(file);
        return result as PendingAttachment;
      } catch (err) {
        devError('file_upload_failed', err);
        showError('Upload failed', `We could not upload ${file.name}.`);
        return null;
      }
    });
    void Promise.all(uploads).then((results) => {
      const successful = results.filter((r): r is PendingAttachment => r !== null);
      if (successful.length > 0) {
        setPendingAttachments((prev) => [...prev, ...successful]);
        showSuccess(
          'Attachments ready',
          `${successful.length} file${successful.length === 1 ? '' : 's'} attached to your next message.`,
        );
      }
      setIsUploading(false);
    });
  }, [showError, showInfo, showSuccess]);

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
      showSuccess('Message removed');
    },
    [messages, applyMessages, showSuccess]
  );

  const copyMessage = useCallback(async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      devLog('Message copied to clipboard');
      showSuccess('Copied to clipboard');
    } catch (err) {
      devError('Failed to copy message:', err);
      showError('Copy failed', 'We could not copy that message.');
    }
  }, [showError, showSuccess]);

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
          const response = await chatClient.chatCompletion(messagesUpToRegeneration, selectedModel || undefined);
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

          const assistantMsg = createAssistantMessage(result ?? {});

          applyMessages([...messagesUpToRegeneration, assistantMsg]);
          showSuccess('Response regenerated');
        }
      } catch (error) {
        devError('Failed to regenerate message:', error);
        // Restore messages on error
        setMessages(messages);
        showError('Regeneration failed', 'We could not regenerate that response.');
      } finally {
        setIsSending(false);
        inputRef.current?.focus();
      }
    },
    [messages, isSending, activeThread, selectedModel, selectedProvider, applyMessages, showError, showSuccess]
  );

  const loadOlderMessages = useCallback(async () => {
    if (!hasMoreMessages || isLoadingOlderMessages || !activeBackendThreadId) {
      return;
    }

    setIsLoadingOlderMessages(true);
    try {
      // Request the next batch of older messages
      const nextOffset = messageOffset + 50;
      const response = await chatClient.getConversation(activeBackendThreadId, {
        offset: nextOffset,
        limit: 50,
      });

      if (response.messages && response.messages.length > 0) {
        // Prepend older messages to the beginning
        setMessages(prev => [...response.messages, ...prev]);
        
        // Update pagination state
        const paginationInfo = response.pagination;
        if (paginationInfo) {
          setHasMoreMessages(paginationInfo.has_more ?? false);
          setMessageOffset(paginationInfo.offset ?? 0);
        }
      }
    } catch (error) {
      devError('Failed to load older messages:', error);
    } finally {
      setIsLoadingOlderMessages(false);
    }
  }, [hasMoreMessages, isLoadingOlderMessages, activeBackendThreadId, messageOffset]);

  return {
    messages,
    input,
    isSending,
    isMessagesLoading,
    isLoadingOlderMessages,
    hasMoreMessages,
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
    loadOlderMessages,
  };
};
