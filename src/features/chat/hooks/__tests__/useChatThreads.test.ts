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
  readChatThreads: jest.fn(() => []),
  removeChatMessages: jest.fn(),
  removeChatThread: jest.fn(),
  sortChatThreads: jest.requireActual('../../../../lib/chat-history').sortChatThreads,
  writeChatThreads: jest.fn(),
}));

const { useQuery } = require('@tanstack/react-query') as {
  useQuery: jest.Mock;
};
const { chatClient } = require('../../api') as typeof import('../../api');
const { readChatThreads } = require('../../../../lib/chat-history') as typeof import('../../../../lib/chat-history');
const { useChatThreads } = require('../useChatThreads') as typeof import('../useChatThreads');

describe('useChatThreads', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('merges backend conversations with legacy local threads and sorts by updatedAt', async () => {
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

    expect(merged).toHaveLength(2);
    expect(merged[0]).toEqual(
      expect.objectContaining({
        id: 'conv-backend',
        source: 'backend',
      })
    );
    expect(merged[1]).toEqual(
      expect.objectContaining({
        id: 'legacy-1',
        source: 'legacy-local',
      })
    );
  });
});
