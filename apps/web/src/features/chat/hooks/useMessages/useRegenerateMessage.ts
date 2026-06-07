import { useCallback } from 'react';
import { chatClient } from '../../api';
import { devError } from '@/utils/dev-log';
import { isAuthenticated } from '../../../../utils/auth-session';
import type { ChatMessage, ChatThread } from '../../types';
import { useToast } from '../../../../hooks/useToast';
import { createMessageId, createAssistantMessage } from './factories';

interface RegenerateMessageDeps {
  messages: ChatMessage[];
  isSending: boolean;
  activeThread: ChatThread | null;
  selectedModel?: string;
  selectedProvider?: string;
  applyMessages: (msgs: ChatMessage[]) => void;
  setMessages: (msgs: ChatMessage[]) => void;
  setIsSending: (v: boolean) => void;
  showError: ReturnType<typeof useToast>['showError'];
  showSuccess: ReturnType<typeof useToast>['showSuccess'];
}

export const useRegenerateMessage = ({
  messages,
  isSending,
  activeThread,
  selectedModel,
  selectedProvider,
  applyMessages,
  setMessages,
  setIsSending,
  showError,
  showSuccess,
}: RegenerateMessageDeps): ((messageId: string) => Promise<void>) =>
  useCallback(
    async (messageId: string) => {
      if (isSending) return;

      const messageIndex = messages.findIndex((msg) => msg.id === messageId);
      if (messageIndex === -1) return;

      const messageToRegenerate = messages[messageIndex]!;
      if (messageToRegenerate.role !== 'assistant') return;

      const userMessageIndex = [...messages]
        .slice(0, messageIndex)
        .reverse()
        .findIndex((msg) => msg.role === 'user');

      if (userMessageIndex === -1) return;

      const userMessage = messages[messageIndex - userMessageIndex - 1]!;
      if (userMessage.role !== 'user') return;

      const messagesUpToRegeneration = messages.slice(0, messageIndex);
      setMessages(messagesUpToRegeneration);
      setIsSending(true);

      try {
        if (!isAuthenticated()) {
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
      setMessages,
      setIsSending,
      showError,
      showSuccess,
    ]
  );
