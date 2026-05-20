import type { FormEvent, RefObject } from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { fetchCollections, searchCollectionByName } from '../api';
import { toUiError } from '../../../lib/ui-error';
import type { SearchResult, SearchScope } from '../types';
import { SEARCH_QUICK_QUERIES } from '../../../content/brand';
import { queryKeys } from '../../../lib/query-keys';

export interface SearchState {
  query: string;
  results: SearchResult[];
  error: string | null;
  selectedCollection: string;
  scope: SearchScope;
  quickQueries: string[];
  searching: boolean;
  collectionsLoading: boolean;
  collectionsData: string[] | undefined;
  queryRef: RefObject<HTMLInputElement>;
  setQuery: (value: string) => void;
  setScope: (value: SearchScope) => void;
  setSelectedCollection: (value: string) => void;
  handleSearch: (e: FormEvent) => Promise<void>;
  handleQuickQuery: (value: string) => void;
  handleClear: () => void;
}

export const useSearchResults = (): SearchState => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [selectedCollection, setSelectedCollection] = useState<string>('');
  const [scope, setScope] = useState<SearchScope>('all');
  const queryRef = useRef<HTMLInputElement | null>(null);

  const quickQueries = Array.from(SEARCH_QUICK_QUERIES);

  const collectionsQuery = useQuery({
    queryKey: queryKeys.collections,
    queryFn: fetchCollections,
    staleTime: 60_000,
  });

  const searchMutation = useMutation({
    mutationFn: async ({ collectionName, queryText }: { collectionName: string; queryText: string }) =>
      searchCollectionByName(collectionName, queryText, 20),
  });

  useEffect(() => {
    if (collectionsQuery.data && collectionsQuery.data.length > 0 && !selectedCollection) {
      setSelectedCollection(collectionsQuery.data[0]);
    }
  }, [collectionsQuery.data, selectedCollection]);

  useEffect(() => {
    if (!collectionsQuery.error) return;
    const uiError = toUiError(collectionsQuery.error, {
      code: 'SEARCH_COLLECTIONS_FAILED',
      userMessage: 'We could not load collections. Please try again.',
    });
    setError(uiError.userMessage);
  }, [collectionsQuery.error]);

  const handleSearch = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!query.trim() || !selectedCollection) return;
      setError(null);
      try {
        const resultsByName = await searchMutation.mutateAsync({
          collectionName: selectedCollection,
          queryText: query.trim(),
        });
        setResults(resultsByName);
      } catch (err) {
        const uiError = toUiError(err, {
          code: 'SEARCH_QUERY_FAILED',
          userMessage: 'Search failed. Please try again.',
        });
        setError(uiError.userMessage);
        setResults([]);
      }
    },
    [query, searchMutation, selectedCollection]
  );

  const handleQuickQuery = useCallback((value: string) => {
    setQuery(value);
    queryRef.current?.focus();
  }, []);

  const handleClear = useCallback(() => {
    setQuery('');
    setResults([]);
    setError(null);
    queryRef.current?.focus();
  }, []);

  return {
    query,
    results,
    error,
    selectedCollection,
    scope,
    quickQueries,
    searching: searchMutation.isPending,
    collectionsLoading: collectionsQuery.isLoading,
    collectionsData: collectionsQuery.data,
    queryRef,
    setQuery,
    setScope,
    setSelectedCollection,
    handleSearch,
    handleQuickQuery,
    handleClear,
  };
};
