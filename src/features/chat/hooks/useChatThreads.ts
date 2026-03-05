import { useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { ChatThread } from '../types';
import {
  readChatThreads,
  sortChatThreads,
  writeChatThreads,
} from '../../../lib/chat-history';
import { queryKeys } from '../../../lib/queryClient';

interface ChatThreadInput {
  id: string;
  title?: string;
  snippet?: string;
  createdAt?: string;
  updatedAt?: string;
}

export const useChatThreads = () => {
  const queryClient = useQueryClient();
  const query = useQuery<ChatThread[]>({
    queryKey: queryKeys.chatThreads,
    queryFn: readChatThreads,
    refetchOnWindowFocus: true,
  });

  const upsertThread = useCallback(
    (input: ChatThreadInput) => {
      queryClient.setQueryData<ChatThread[]>(queryKeys.chatThreads, current => {
        const now = new Date().toISOString();
        const list = Array.isArray(current) ? current : [];
        const existing = list.find(thread => thread.id === input.id);
        const nextThread: ChatThread = {
          id: input.id,
          title: input.title ?? existing?.title ?? 'Untitled chat',
          snippet: input.snippet ?? existing?.snippet ?? '',
          createdAt: existing?.createdAt ?? input.createdAt ?? now,
          updatedAt: input.updatedAt ?? now,
        };
        const nextThreads = existing
          ? list.map(thread => (thread.id === input.id ? nextThread : thread))
          : [nextThread, ...list];
        const sorted = sortChatThreads(nextThreads);
        writeChatThreads(sorted);
        return sorted;
      });
    },
    [queryClient]
  );

  const removeThread = useCallback(
    (id: string) => {
      queryClient.setQueryData<ChatThread[]>(queryKeys.chatThreads, current => {
        const list = Array.isArray(current) ? current : [];
        const next = list.filter(thread => thread.id !== id);
        writeChatThreads(next);
        return next;
      });
    },
    [queryClient]
  );

  return {
    threads: query.data ?? [],
    isLoading: query.isLoading,
    upsertThread,
    removeThread,
  };
};
