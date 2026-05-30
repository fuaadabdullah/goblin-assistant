import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { renderHook } from '@testing-library/react';

jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn(),
  useQueryClient: jest.fn(() => ({
    setQueryData: jest.fn(),
    invalidateQueries: jest.fn(),
  })),
}));

jest.mock('../../api', () => ({
  chatClient: {
    listConversations: jest.fn(),
  },
}));

jest.mock('../../../../lib/chat-history', () => ({
  buildThreadKey: jest.requireActual('../../../../lib/chat-history').buildThreadKey,
  markChatMigrationCompleted: jest.fn(),
  readChatThreads: jest.fn(() => []),
  readChatMigrationMeta: jest.fn(() => ({ migrationCompleted: false })),
  removeChatMessages: jest.fn(),
  removeChatThread: jest.fn(),
  sortChatThreads: jest.requireActual('../../../../lib/chat-history').sortChatThreads,
  writeChatThreads: jest.fn(),
}));

const { useQuery } = require('@tanstack/react-query') as {
  useQuery: jest.Mock;
};
const { chatClient } = require('../../api') as typeof import('../../api');
const { markChatMigrationCompleted, readChatMigrationMeta, readChatThreads } =
  require('../../../../lib/chat-history') as typeof import('../../../../lib/chat-history');
const { useChatThreads } = require('../useChatThreads') as typeof import('../useChatThreads');

describe('useChatThreads', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('prefers backend conversations and marks migration complete after hydration', async () => {
    (chatClient.listConversations as jest.Mock).mockResolvedValue([
      {
        conversationId: 'conv-backend',
        title: 'Backend thread',
        snippet: 'Remote',
        createdAt: '2026-03-07T10:00:00.000Z',
        updatedAt: '2026-03-07T12:00:00.000Z',
        messageCount: 2,
      },
    ]);
    (readChatThreads as jest.Mock).mockReturnValue([
      {
        id: 'legacy-1',
        source: 'legacy-local',
        threadKey: 'legacy-local:legacy-1',
        title: 'Legacy thread',
        snippet: 'Local',
        createdAt: '2026-03-07T09:00:00.000Z',
        updatedAt: '2026-03-07T11:00:00.000Z',
      },
    ]);
    useQuery.mockImplementation(({ queryFn }: { queryFn: () => Promise<unknown> }) => ({
      data: undefined,
      isLoading: false,
      queryFn,
    }));

    renderHook(() => useChatThreads());
    const merged = await (useQuery.mock.calls[0][0].queryFn as () => Promise<any>)();

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
    (readChatMigrationMeta as jest.Mock).mockReturnValue({
      migrationCompleted: true,
      completedAt: '2026-03-07T13:00:00.000Z',
    });
    (chatClient.listConversations as jest.Mock).mockResolvedValue([
      {
        conversationId: 'conv-backend',
        title: 'Backend thread',
        snippet: 'Remote',
        createdAt: '2026-03-07T10:00:00.000Z',
        updatedAt: '2026-03-07T12:00:00.000Z',
        messageCount: 2,
      },
    ]);
    (readChatThreads as jest.Mock).mockReturnValue([
      {
        id: 'legacy-1',
        source: 'legacy-local',
        threadKey: 'legacy-local:legacy-1',
        title: 'Legacy thread',
        snippet: 'Local',
        createdAt: '2026-03-07T09:00:00.000Z',
        updatedAt: '2026-03-07T11:00:00.000Z',
      },
    ]);
    useQuery.mockImplementation(({ queryFn }: { queryFn: () => Promise<unknown> }) => ({
      data: undefined,
      isLoading: false,
      queryFn,
    }));

    renderHook(() => useChatThreads());
    const merged = await (useQuery.mock.calls[0][0].queryFn as () => Promise<any>)();

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
    (readChatMigrationMeta as jest.Mock).mockReturnValue({
      migrationCompleted: false,
    });
    (chatClient.listConversations as jest.Mock).mockRejectedValue(new Error('network'));
    (readChatThreads as jest.Mock).mockReturnValue([
      {
        id: 'legacy-1',
        source: 'legacy-local',
        threadKey: 'legacy-local:legacy-1',
        title: 'Legacy thread',
        snippet: 'Local',
        createdAt: '2026-03-07T09:00:00.000Z',
        updatedAt: '2026-03-07T11:00:00.000Z',
      },
    ]);
    useQuery.mockImplementation(({ queryFn }: { queryFn: () => Promise<unknown> }) => ({
      data: undefined,
      isLoading: false,
      queryFn,
    }));

    renderHook(() => useChatThreads());
    const merged = await (useQuery.mock.calls[0][0].queryFn as () => Promise<any>)();

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
