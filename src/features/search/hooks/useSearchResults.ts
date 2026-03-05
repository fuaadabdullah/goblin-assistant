import type { FormEvent, RefObject } from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchCollections, searchCollectionByName } from '../api';
import { toUiError } from '../../../lib/ui-error';
import type { SearchResult, SearchScope } from '../types';
import { SEARCH_QUICK_QUERIES } from '../../../content/brand';

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

  const [collectionsData, setCollectionsData] = useState<string[] | undefined>(undefined);
  const [collectionsLoading, setCollectionsLoading] = useState(true);
  const [searching, setSearching] = useState(false);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        setCollectionsLoading(true);
        const collections = await fetchCollections();
        if (!active) return;
        setCollectionsData(collections);
        if (collections.length > 0 && !selectedCollection) {
          setSelectedCollection(collections[0]);
        }
      } catch (err) {
        if (!active) return;
        const uiError = toUiError(err, {
          code: 'SEARCH_COLLECTIONS_FAILED',
          userMessage: 'We could not load collections. Please try again.',
        });
        setError(uiError.userMessage);
        setCollectionsData([]);
      } finally {
        if (active) setCollectionsLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, []);

  const handleSearch = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      if (!query.trim() || !selectedCollection) return;
      setError(null);
      try {
        setSearching(true);
        const resultsByName = await searchCollectionByName(
          selectedCollection,
          query.trim(),
          20
        );
        setResults(resultsByName);
      } catch (err) {
        const uiError = toUiError(err, {
          code: 'SEARCH_QUERY_FAILED',
          userMessage: 'Search failed. Please try again.',
        });
        setError(uiError.userMessage);
        setResults([]);
      } finally {
        setSearching(false);
      }
    },
    [query, selectedCollection]
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
    searching,
    collectionsLoading,
    collectionsData,
    queryRef,
    setQuery,
    setScope,
    setSelectedCollection,
    handleSearch,
    handleQuickQuery,
    handleClear,
  };
};
