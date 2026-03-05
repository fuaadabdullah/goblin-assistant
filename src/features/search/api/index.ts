import { apiClient } from '../../../api/apiClient';
import { UiError } from '../../../lib/ui-error';
import type { SearchResult } from '../types';

interface SearchResponse {
  results: SearchResult[];
  total_results: number;
}

export const fetchCollections = async (): Promise<string[]> => {
  try {
    return await apiClient.getSearchCollections();
  } catch (error) {
    throw new UiError(
      {
        code: 'SEARCH_COLLECTIONS_FAILED',
        userMessage: 'We could not load collections. Please refresh and try again.',
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
        userMessage: 'Search could not complete. Please try again in a moment.',
      },
      error
    );
  }
};
