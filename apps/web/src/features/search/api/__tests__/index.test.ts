import { beforeEach, describe, expect, it, vi } from 'vitest';

const { mockGetSearchCollections, mockSearchQuery } = vi.hoisted(() => ({
  mockGetSearchCollections: vi.fn(),
  mockSearchQuery: vi.fn(),
}));

vi.mock('@/lib/api', () => ({
  apiClient: {
    getSearchCollections: mockGetSearchCollections,
    searchQuery: mockSearchQuery,
  },
}));

import { fetchCollections, searchCollectionByName } from '../index';

describe('search api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('preserves collection load error messages', async () => {
    mockGetSearchCollections.mockRejectedValueOnce(new Error('Search index offline'));

    await expect(fetchCollections()).rejects.toMatchObject({
      code: 'SEARCH_COLLECTIONS_FAILED',
      userMessage: 'Search index offline',
    });
  });

  it('preserves query error messages', async () => {
    mockSearchQuery.mockRejectedValueOnce(new Error('Query service unavailable'));

    await expect(searchCollectionByName('docs', 'test')).rejects.toMatchObject({
      code: 'SEARCH_QUERY_FAILED',
      userMessage: 'Query service unavailable',
    });
  });

  it('preserves non-Error collection load failures', async () => {
    mockGetSearchCollections.mockRejectedValueOnce('search index unavailable');

    await expect(fetchCollections()).rejects.toMatchObject({
      code: 'SEARCH_COLLECTIONS_FAILED',
      userMessage: 'search index unavailable',
    });
  });
});
