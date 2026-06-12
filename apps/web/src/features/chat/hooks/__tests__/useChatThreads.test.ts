import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
  useQueryClient: vi.fn(() => ({
    setQueryData: vi.fn(),
    invalidateQueries: vi.fn(),
  })),
}));

vi.mock('../../api', () => ({
  chatClient: {
    listConversations: vi.fn(),
  },
}));

vi.mock('../../../../lib/chat-history', async () => {
  const actual = await vi.importActual<typeof import('../../../../lib/chat-history')>(
    '../../../../lib/chat-history'
  );
  return {
    buildThreadKey: actual.buildThreadKey,
    markChatMigrationCompleted: vi.fn(),
    readChatThreads: vi.fn(() => []),
    readChatMigrationMeta: vi.fn(() => ({ migrationCompleted: false })),
    removeChatMessages: vi.fn(),
    removeChatThread: vi.fn(),
    sortChatThreads: actual.sortChatThreads,
    writeChatThreads: vi.fn(),
  };
});

import { useQuery } from '@tanstack/react-query';
import { chatClient } from '../../api';
import {
  markChatMigrationCompleted,
  readChatMigrationMeta,
  readChatThreads,
} from '../../../../lib/chat-history';
import { useChatThreads } from '../useChatThreads';

describe('useChatThreads', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('prefers backend conversations and marks migration complete after hydration', async () => {
    vi.mocked(chatClient.listConversations).mockResolvedValue([
      {
        conversationId: 'conv-backend',
        title: 'Backend thread',
        snippet: 'Remote',
        createdAt: '2026-03-07T10:00:00.000Z',
        updatedAt: '2026-03-07T12:00:00.000Z',
        messageCount: 2,
      },
    ] as never);
    vi.mocked(readChatThreads).mockReturnValue([
      {
        id: 'legacy-1',
        source: 'legacy-local',
        threadKey: 'legacy-local:legacy-1',
        title: 'Legacy thread',
        snippet: 'Local',
        createdAt: '2026-03-07T09:00:00.000Z',
        updatedAt: '2026-03-07T11:00:00.000Z',
      },
    ] as never);
    vi.mocked(useQuery).mockImplementation(
      ({ queryFn }: { queryFn: () => Promise<unknown> }) =>
        ({
          data: undefined,
          isLoading: false,
          queryFn,
        }) as never
    );

    renderHook(() => useChatThreads());
    const merged = await (vi.mocked(useQuery).mock.calls[0][0].queryFn as () => Promise<any>)();

    expect(merged).toHaveLength(1);
    expect(merged[0]).toEqual(
      expect.objectContaining({
        id: 'conv-backend',
        source: 'backend',
      })
    );
    expect(markChatMigrationCompleted).toHaveBeenCalledTimes(1);
  });

  it('does not include legacy threads after migration completion', async () => {
    vi.mocked(readChatMigrationMeta).mockReturnValue({
      migrationCompleted: true,
      completedAt: '2026-03-07T13:00:00.000Z',
    } as never);
    vi.mocked(chatClient.listConversations).mockResolvedValue([
      {
        conversationId: 'conv-backend',
        title: 'Backend thread',
        snippet: 'Remote',
        createdAt: '2026-03-07T10:00:00.000Z',
        updatedAt: '2026-03-07T12:00:00.000Z',
        messageCount: 2,
      },
    ] as never);
    vi.mocked(readChatThreads).mockReturnValue([
      {
        id: 'legacy-1',
        source: 'legacy-local',
        threadKey: 'legacy-local:legacy-1',
        title: 'Legacy thread',
        snippet: 'Local',
        createdAt: '2026-03-07T09:00:00.000Z',
        updatedAt: '2026-03-07T11:00:00.000Z',
      },
    ] as never);
    vi.mocked(useQuery).mockImplementation(
      ({ queryFn }: { queryFn: () => Promise<unknown> }) =>
        ({
          data: undefined,
          isLoading: false,
          queryFn,
        }) as never
    );

    renderHook(() => useChatThreads());
    const merged = await (vi.mocked(useQuery).mock.calls[0][0].queryFn as () => Promise<any>)();

    expect(merged).toHaveLength(1);
    expect(merged[0]).toEqual(
      expect.objectContaining({
        id: 'conv-backend',
        source: 'backend',
      })
    );
    expect(readChatThreads).not.toHaveBeenCalled();
    expect(markChatMigrationCompleted).not.toHaveBeenCalled();
  });

  it('keeps migration incomplete when backend hydration fails', async () => {
    vi.mocked(readChatMigrationMeta).mockReturnValue({
      migrationCompleted: false,
    } as never);
    vi.mocked(chatClient.listConversations).mockRejectedValue(new Error('network'));
    vi.mocked(readChatThreads).mockReturnValue([
      {
        id: 'legacy-1',
        source: 'legacy-local',
        threadKey: 'legacy-local:legacy-1',
        title: 'Legacy thread',
        snippet: 'Local',
        createdAt: '2026-03-07T09:00:00.000Z',
        updatedAt: '2026-03-07T11:00:00.000Z',
      },
    ] as never);
    vi.mocked(useQuery).mockImplementation(
      ({ queryFn }: { queryFn: () => Promise<unknown> }) =>
        ({
          data: undefined,
          isLoading: false,
          queryFn,
        }) as never
    );

    renderHook(() => useChatThreads());
    const merged = await (vi.mocked(useQuery).mock.calls[0][0].queryFn as () => Promise<any>)();

    expect(merged).toHaveLength(1);
    expect(merged[0]).toEqual(
      expect.objectContaining({
        id: 'legacy-1',
        source: 'legacy-local',
      })
    );
    expect(markChatMigrationCompleted).not.toHaveBeenCalled();
  });
});
