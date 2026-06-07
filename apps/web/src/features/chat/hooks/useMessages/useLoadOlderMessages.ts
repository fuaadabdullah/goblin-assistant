import { useCallback, type Dispatch, type SetStateAction } from 'react';
import { chatClient } from '../../api';
import { devError } from '@/utils/dev-log';
import type { ChatMessage } from '../../types';

interface LoadOlderMessagesDeps {
  hasMoreMessages: boolean;
  isLoadingOlderMessages: boolean;
  activeBackendThreadId: string | null;
  messageOffset: number;
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  setHasMoreMessages: (v: boolean) => void;
  setMessageOffset: (v: number) => void;
  setIsLoadingOlderMessages: (v: boolean) => void;
}

export const useLoadOlderMessages = ({
  hasMoreMessages,
  isLoadingOlderMessages,
  activeBackendThreadId,
  messageOffset,
  setMessages,
  setHasMoreMessages,
  setMessageOffset,
  setIsLoadingOlderMessages,
}: LoadOlderMessagesDeps): (() => Promise<void>) =>
  useCallback(async () => {
    if (!hasMoreMessages || isLoadingOlderMessages || !activeBackendThreadId) return;

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
  }, [
    hasMoreMessages,
    isLoadingOlderMessages,
    activeBackendThreadId,
    messageOffset,
    setMessages,
    setHasMoreMessages,
    setMessageOffset,
    setIsLoadingOlderMessages,
  ]);
