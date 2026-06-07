import { useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { chatClient } from '../../api';
import { toUiError } from '../../../../lib/ui-error';
import type { ChatMessage, ChatThread } from '../../types';
import { buildThreadKey } from '../../../../lib/chat-history';
import { queryKeys } from '../../../../lib/query-keys';
import { useToast } from '../../../../hooks/useToast';
import { isAuthenticated } from '../../../../utils/auth-session';
import type { PendingAttachment } from '../useChatSession';
import { createMessageId, createAssistantMessage, mapAttachments } from './factories';

interface SendMessageDeps {
  input: string;
  isSending: boolean;
  isMessagesLoading: boolean;
  messages: ChatMessage[];
  activeThread: ChatThread | null;
  selectedModel?: string;
  selectedProvider?: string;
  pendingAttachments: PendingAttachment[];
  applyMessages: (msgs: ChatMessage[]) => void;
  onThreadUpdated?: (thread: ChatThread) => void;
  onThreadRemoved?: (thread: ChatThread) => void;
  onThreadsInvalidated?: () => void;
  setIsSending: (v: boolean) => void;
  showError: ReturnType<typeof useToast>['showError'];
  showInfo: ReturnType<typeof useToast>['showInfo'];
}

export const useSendMessage = ({
  input,
  isSending,
  isMessagesLoading,
  messages,
  activeThread,
  selectedModel,
  selectedProvider,
  pendingAttachments,
  applyMessages,
  onThreadUpdated,
  onThreadRemoved,
  onThreadsInvalidated,
  setIsSending,
  showError,
  showInfo,
}: SendMessageDeps): ((messageOverride?: string) => Promise<void>) => {
  const queryClient = useQueryClient();

  return useCallback(
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
      applyMessages(updatedMessages);

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
            return { ...current, updatedAt: assistantMsg.createdAt, messages: nextMessages };
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
      setIsSending,
      showError,
      showInfo,
    ]
  );
};
