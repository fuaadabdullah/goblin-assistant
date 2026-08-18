import { apiClient } from '@/lib/api';
import { UiError } from '../../../lib/ui-error';
import { getUserMessage } from '../../../lib/error/toast';
import type { SearchResult } from '../types';

interface SearchResponse {
  results: SearchResult[];
  total_results: number;
}

export const fetchCollections = async (): Promise<string[]> => {
  try {
    return (await apiClient.getSearchCollections()) as string[];
  } catch (error) {
    throw new UiError(
      {
        code: 'SEARCH_COLLECTIONS_FAILED',
        userMessage: getUserMessage(error),
      },
      error
    );
  }
};

export const searchCollectionByName = async (
  collectionName: string,
  query: string,
  limit = 20
): Promise<SearchResult[]> => {
  try {
    const data = await apiClient.searchQuery(collectionName, query, limit);
    return ((data as SearchResponse)?.results || []) as SearchResult[];
  } catch (error) {
    throw new UiError(
      {
        code: 'SEARCH_QUERY_FAILED',
        userMessage: getUserMessage(error),
      },
      error
    );
  }
};
