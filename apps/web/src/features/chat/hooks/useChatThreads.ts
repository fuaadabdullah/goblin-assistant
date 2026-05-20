import { useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { ChatThread, ChatThreadSource } from '../types';
import { chatClient } from '../api';
import {
  buildThreadKey,
  readChatThreads,
  removeChatMessages,
  removeChatThread,
  sortChatThreads,
  writeChatThreads,
} from '../../../lib/chat-history';
import { queryKeys } from '../../../lib/query-keys';

interface ChatThreadInput {
  id: string;
  source?: ChatThreadSource;
  title?: string;
  snippet?: string;
  createdAt?: string;
  updatedAt?: string;
}

const createThread = (input: ChatThreadInput, existing?: ChatThread): ChatThread => {
  const source = input.source ?? existing?.source ?? 'backend';
  const now = new Date().toISOString();

  return {
    id: input.id,
    source,
    threadKey: buildThreadKey(source, input.id),
    title: input.title ?? existing?.title ?? 'Untitled chat',
    snippet: input.snippet ?? existing?.snippet ?? '',
    createdAt: existing?.createdAt ?? input.createdAt ?? now,
    updatedAt: input.updatedAt ?? existing?.updatedAt ?? now,
  };
};

const mapBackendThread = (thread: Awaited<ReturnType<typeof chatClient.listConversations>>[number]): ChatThread => ({
  id: thread.conversationId,
  source: 'backend',
  threadKey: buildThreadKey('backend', thread.conversationId),
  title: thread.title || 'Untitled chat',
  snippet: thread.snippet || '',
  createdAt: thread.createdAt,
  updatedAt: thread.updatedAt,
});

const readLegacyThreads = (): ChatThread[] => readChatThreads();

const writeLegacyThreads = (threads: ChatThread[]): void => {
  writeChatThreads(threads.filter(thread => thread.source === 'legacy-local'));
};

export const useChatThreads = () => {
  const queryClient = useQueryClient();
  const query = useQuery<ChatThread[]>({
    queryKey: queryKeys.chatThreads,
    queryFn: async () => {
      const legacyThreads = readLegacyThreads();

      try {
        const backendThreads = await chatClient.listConversations();
      return sortChatThreads([
          ...backendThreads.map(mapBackendThread),
          ...legacyThreads,
        ]);
      } catch {
        return sortChatThreads(legacyThreads);
      }
    },
    refetchOnWindowFocus: true,
  });

  const upsertThread = useCallback(
    (input: ChatThreadInput) => {
      queryClient.setQueryData<ChatThread[]>(
        queryKeys.chatThreads,
        (current: ChatThread[] | undefined) => {
          const list = Array.isArray(current) ? current : [];
          const threadKey = buildThreadKey(input.source ?? 'backend', input.id);
          const existing = list.find(thread => thread.threadKey === threadKey);
          const nextThread = createThread(input, existing);
          const nextThreads = existing
            ? list.map(thread => (thread.threadKey === threadKey ? nextThread : thread))
            : [nextThread, ...list];
          const sorted = sortChatThreads(nextThreads);
          writeLegacyThreads(sorted);
          return sorted;
        }
      );
    },
    [queryClient]
  );

  const removeThread = useCallback(
    (thread: Pick<ChatThread, 'id' | 'source' | 'threadKey'>) => {
      queryClient.setQueryData<ChatThread[]>(
        queryKeys.chatThreads,
        (current: ChatThread[] | undefined) => {
          const list = Array.isArray(current) ? current : [];
          const next = list.filter(item => item.threadKey !== thread.threadKey);
          if (thread.source === 'legacy-local') {
            removeChatThread(thread.id);
            removeChatMessages(thread.id);
          } else {
            writeLegacyThreads(next);
          }
          return next;
        }
      );
    },
    [queryClient]
  );

  const invalidateThreads = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.chatThreads });
  }, [queryClient]);

  return {
    threads: query.data ?? [],
    isLoading: query.isLoading,
    upsertThread,
    removeThread,
    invalidateThreads,
  };
};
