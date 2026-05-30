import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { chatClient } from '../api';
import { toUiError } from '../../../lib/ui-error';
import type { ChatMessage, ChatThread } from '../types';
import { buildThreadKey, readChatMessages } from '../../../lib/chat-history';
import { queryKeys } from '../../../lib/query-keys';
import { useToast } from '../../../contexts/ToastContext';
import { isAuthenticated } from '../../../utils/auth-session';
import { devError, devLog } from '@/utils/dev-log';
import { computeCostUsd } from '../../../lib/llm-rates';
import type { ChatMessageMeta, ChatUsage } from '../../../domain/chat';
import type { PendingAttachment } from './useChatSession';

export interface MessagesState {
  messages: ChatMessage[];
  isSending: boolean;
  isMessagesLoading: boolean;
  isLoadingOlderMessages: boolean;
  hasMoreMessages: boolean;
  totalTokens: number;
  totalCostUsd: number;
  sendMessage: (messageOverride?: string) => Promise<void>;
  deleteMessage: (messageId: string) => void;
  copyMessage: (content: string) => Promise<void>;
  regenerateMessage: (messageId: string) => Promise<void>;
  loadOlderMessages: () => Promise<void>;
  setMessages: (messages: ChatMessage[]) => void;
}

export interface MessagesProps {
  input: string;
  activeThread: ChatThread | null;
  activeBackendThreadId: string | null;
  selectedProvider?: string;
  selectedModel?: string;
  pendingAttachments: PendingAttachment[];
  onMessagesLoading?: (loading: boolean) => void;
  onThreadUpdated?: (thread: ChatThread) => void;
  onThreadRemoved?: (thread: ChatThread) => void;
  onThreadsInvalidated?: () => void;
  backendConversationQuery?: {
    isLoading: boolean;
    isFetching: boolean;
    data?: {
      conversationId: string;
      title: string;
      createdAt: string;
      updatedAt: string;
      messages: ChatMessage[];
      pagination?: { has_more?: boolean; offset?: number };
    };
  };
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

const createAssistantMessage = (response: {
  messageId?: string;
  createdAt?: string;
  content?: string;
  provider?: string;
  model?: string;
  usage?: ChatUsage;
  cost_usd?: number;
  correlation_id?: string;
  visualizations?: ChatMessageMeta['visualizations'];
}): ChatMessage => {
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

/**
 * Manages chat messages: sending, regenerating, deleting, copying, and pagination
 */
export const useMessages = ({
  input,
  activeThread,
  activeBackendThreadId,
  selectedProvider,
  selectedModel,
  pendingAttachments,
  onMessagesLoading,
  onThreadUpdated,
  onThreadRemoved,
  onThreadsInvalidated,
  backendConversationQuery,
}: MessagesProps): MessagesState => {
  const { showError, showInfo, showSuccess } = useToast();
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [totalTokens, setTotalTokens] = useState(0);
  const [totalCostUsd, setTotalCostUsd] = useState(0);
  const [isLoadingOlderMessages, setIsLoadingOlderMessages] = useState(false);
  const [hasMoreMessages, setHasMoreMessages] = useState(true);
  const [messageOffset, setMessageOffset] = useState(0);

  const isMessagesLoading =
    activeThread?.source === 'backend' && backendConversationQuery && !backendConversationQuery.data
      ? backendConversationQuery.isLoading || backendConversationQuery.isFetching
      : false;

  const applyMessages = useCallback((nextMessages: ChatMessage[]) => {
    setMessages(nextMessages);
    const totals = calculateTotals(nextMessages);
    setTotalTokens(totals.totalTokens);
    setTotalCostUsd(totals.totalCostUsd);
  }, []);

  const sendMessage = useCallback(
    async (messageOverride?: string) => {
      const content = (messageOverride ?? input).trim();
      if (!content || isSending || isMessagesLoading) return;

      setIsSending(true);

      const nowIso = new Date().toISOString();
      const userMsg: ChatMessage = {
        id: createMessageId(),
        createdAt: nowIso,
        role: 'user',
        content,
        meta: {
          ...(pendingAttachments.length > 0
            ? { attachments: mapAttachments(pendingAttachments) }
            : {}),
        },
      };
      const previousMessages = messages;
      const updatedMessages = [...previousMessages, userMsg];
      setMessages(updatedMessages);

      try {
        const isAuthed = isAuthenticated();

        if (!isAuthed) {
          const response = await chatClient.chatCompletion(
            updatedMessages,
            selectedModel || undefined
          );
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
          attachment_ids:
            pendingAttachments.length > 0 ? pendingAttachments.map((a) => a.file_id) : undefined,
        });

        const assistantMsg = createAssistantMessage(result ?? {});
        const nextMessages = [...updatedMessages, assistantMsg];
        applyMessages(nextMessages);

        queryClient.setQueryData(
          queryKeys.chatConversation(conversationId),
          (
            current:
              | {
                  conversationId: string;
                  title: string;
                  createdAt: string;
                  updatedAt: string;
                  messages: ChatMessage[];
                }
              | undefined
          ) => {
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
          }
        );

        const backendThreadKey = buildThreadKey('backend', conversationId);
        if (onThreadUpdated) {
          onThreadUpdated({
            id: conversationId,
            source: 'backend',
            title: pendingThreadTitle,
            snippet: assistantMsg.content,
            createdAt,
            updatedAt: assistantMsg.createdAt,
            threadKey: backendThreadKey,
          } as ChatThread);
        }

        if (shouldPromoteLegacy && activeThread && onThreadRemoved) {
          onThreadRemoved(activeThread);
        }

        if (onThreadsInvalidated) {
          onThreadsInvalidated();
        }
      } catch (err: unknown) {
        const uiError = toUiError(err, {
          code: 'CHAT_SEND_FAILED',
          userMessage: 'Sorry, we could not send that message right now.',
        });

        if (uiError.code === 'AUTHENTICATION_REQUIRED') {
          showInfo('Sign in required', 'Sign in to continue this conversation.');
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
      }
    },
    [
      input,
      isSending,
      isMessagesLoading,
      messages,
      activeThread,
      selectedModel,
      selectedProvider,
      pendingAttachments,
      applyMessages,
      queryClient,
      onThreadUpdated,
      onThreadRemoved,
      onThreadsInvalidated,
      showError,
      showInfo,
    ]
  );

  const deleteMessage = useCallback(
    (messageId: string) => {
      const filteredMessages = messages.filter((msg) => msg.id !== messageId);
      applyMessages(filteredMessages);
      showSuccess('Message removed');
    },
    [messages, applyMessages, showSuccess]
  );

  const copyMessage = useCallback(
    async (content: string) => {
      try {
        await navigator.clipboard.writeText(content);
        devLog('Message copied to clipboard');
        showSuccess('Copied to clipboard');
      } catch (err) {
        devError('Failed to copy message:', err);
        showError('Copy failed', 'We could not copy that message.');
      }
    },
    [showError, showSuccess]
  );

  const regenerateMessage = useCallback(
    async (messageId: string) => {
      if (isSending) return;

      const messageIndex = messages.findIndex((msg) => msg.id === messageId);
      if (messageIndex === -1) return;

      const messageToRegenerate = messages[messageIndex];
      if (messageToRegenerate.role !== 'assistant') return;

      const userMessageIndex = [...messages]
        .slice(0, messageIndex)
        .reverse()
        .findIndex((msg) => msg.role === 'user');

      if (userMessageIndex === -1) return;

      const userMessage = messages[messageIndex - userMessageIndex - 1];
      if (userMessage.role !== 'user') return;

      const messagesUpToRegeneration = messages.slice(0, messageIndex);
      setMessages(messagesUpToRegeneration);
      setIsSending(true);

      try {
        const isAuthed = isAuthenticated();

        if (!isAuthed) {
          const response = await chatClient.chatCompletion(
            messagesUpToRegeneration,
            selectedModel || undefined
          );
          const text = typeof response === 'string' ? response : String(response ?? 'No response');
          const assistantMsg: ChatMessage = {
            id: createMessageId(),
            createdAt: new Date().toISOString(),
            role: 'assistant',
            content: text,
          };
          applyMessages([...messagesUpToRegeneration, assistantMsg]);
        } else {
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
        setMessages(messages);
        showError('Regeneration failed', 'We could not regenerate that response.');
      } finally {
        setIsSending(false);
      }
    },
    [
      messages,
      isSending,
      activeThread,
      selectedModel,
      selectedProvider,
      applyMessages,
      showError,
      showSuccess,
    ]
  );

  const loadOlderMessages = useCallback(async () => {
    if (!hasMoreMessages || isLoadingOlderMessages || !activeBackendThreadId) {
      return;
    }

    setIsLoadingOlderMessages(true);
    try {
      const nextOffset = messageOffset + 50;
      const response = await chatClient.getConversation(activeBackendThreadId, {
        offset: nextOffset,
        limit: 50,
      });

      if (response.messages && response.messages.length > 0) {
        setMessages((prev) => [...response.messages, ...prev]);

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
    isSending,
    isMessagesLoading,
    isLoadingOlderMessages,
    hasMoreMessages,
    totalTokens,
    totalCostUsd,
    sendMessage,
    deleteMessage,
    copyMessage,
    regenerateMessage,
    loadOlderMessages,
    setMessages,
  };
};
