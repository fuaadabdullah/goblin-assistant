import { useCallback, useState } from 'react';
import { useToast } from '../../../../contexts/ToastContext';
import { calculateTotals } from './factories';
import { useSendMessage } from './useSendMessage';
import { useDeleteMessage } from './useDeleteMessage';
import { useCopyMessage } from './useCopyMessage';
import { useRegenerateMessage } from './useRegenerateMessage';
import { useLoadOlderMessages } from './useLoadOlderMessages';
import type { ChatMessage } from '../../types';
import type { MessagesProps, MessagesState } from './types';

export type { MessagesState, MessagesProps };

export const useMessages = ({
  input,
  activeThread,
  activeBackendThreadId,
  selectedProvider,
  selectedModel,
  pendingAttachments,
  onThreadUpdated,
  onThreadRemoved,
  onThreadsInvalidated,
  backendConversationQuery,
}: MessagesProps): MessagesState => {
  const { showError, showInfo, showSuccess } = useToast();

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

  const sendMessage = useSendMessage({
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
  });

  const deleteMessage = useDeleteMessage({ messages, applyMessages, showSuccess });

  const copyMessage = useCopyMessage({ showError, showSuccess });

  const regenerateMessage = useRegenerateMessage({
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
  });

  const loadOlderMessages = useLoadOlderMessages({
    hasMoreMessages,
    isLoadingOlderMessages,
    activeBackendThreadId,
    messageOffset,
    setMessages,
    setHasMoreMessages,
    setMessageOffset,
    setIsLoadingOlderMessages,
  });

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
    setMessages: applyMessages,
  };
};
