import React from 'react';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/content/brand', () => ({
  SEARCH_QUICK_QUERIES: ['hello world', 'test query'],
}));

const mockFetchCollections = vi.fn().mockResolvedValue(['docs', 'code']);
const mockSearchCollectionByName = vi
  .fn()
  .mockResolvedValue([{ id: '1', content: 'result 1', score: 0.9 }]);

vi.mock('../../api', () => ({
  fetchCollections: (...args: unknown[]) => mockFetchCollections(...args),
  searchCollectionByName: (...args: unknown[]) => mockSearchCollectionByName(...args),
}));

vi.mock('@/lib/query-keys', () => ({
  queryKeys: { collections: ['collections'] },
}));

import { useSearchResults } from '../useSearchResults';

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe('useSearchResults', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns initial state', () => {
    const { result } = renderHook(() => useSearchResults(), { wrapper });
    expect(result.current.query).toBe('');
    expect(result.current.results).toEqual([]);
    expect(result.current.error).toBeNull();
    expect(result.current.scope).toBe('all');
    expect(result.current.quickQueries).toEqual(['hello world', 'test query']);
  });

  it('loads collections on mount', async () => {
    const { result } = renderHook(() => useSearchResults(), { wrapper });
    await waitFor(() => {
      expect(result.current.collectionsData).toEqual(['docs', 'code']);
    });
    expect(result.current.selectedCollection).toBe('docs');
  });

  it('setQuery updates the query', () => {
    const { result } = renderHook(() => useSearchResults(), { wrapper });
    act(() => {
      result.current.setQuery('new query');
    });
    expect(result.current.query).toBe('new query');
  });

  it('setScope updates the scope', () => {
    const { result } = renderHook(() => useSearchResults(), { wrapper });
    act(() => {
      result.current.setScope('documents');
    });
    expect(result.current.scope).toBe('documents');
  });

  it('handleSearch calls search mutation', async () => {
    const { result } = renderHook(() => useSearchResults(), { wrapper });
    await waitFor(() => expect(result.current.selectedCollection).toBe('docs'));
    act(() => {
      result.current.setQuery('test');
    });
    const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(async () => {
      await result.current.handleSearch(mockEvent);
    });
    expect(mockSearchCollectionByName).toHaveBeenCalledWith('docs', 'test', 20);
    expect(result.current.results).toHaveLength(1);
  });

  it('handleSearch does nothing if query is empty', async () => {
    const { result } = renderHook(() => useSearchResults(), { wrapper });
    const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(async () => {
      await result.current.handleSearch(mockEvent);
    });
    expect(mockSearchCollectionByName).not.toHaveBeenCalled();
  });

  it('handleSearch sets error on failure', async () => {
    mockSearchCollectionByName.mockRejectedValueOnce(new Error('Search service unavailable'));
    const { result } = renderHook(() => useSearchResults(), { wrapper });
    await waitFor(() => expect(result.current.selectedCollection).toBe('docs'));
    act(() => {
      result.current.setQuery('test');
    });
    const mockEvent = { preventDefault: vi.fn() } as unknown as React.FormEvent;
    await act(async () => {
      await result.current.handleSearch(mockEvent);
    });
    expect(result.current.error).toBe('Search service unavailable');
    expect(result.current.results).toEqual([]);
  });

  it('handleQuickQuery sets query', () => {
    const { result } = renderHook(() => useSearchResults(), { wrapper });
    act(() => {
      result.current.handleQuickQuery('quick test');
    });
    expect(result.current.query).toBe('quick test');
  });

  it('handleClear resets state', async () => {
    const { result } = renderHook(() => useSearchResults(), { wrapper });
    act(() => {
      result.current.setQuery('test');
    });
    act(() => {
      result.current.handleClear();
    });
    expect(result.current.query).toBe('');
    expect(result.current.results).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it('sets error when collections fail to load', async () => {
    mockFetchCollections.mockRejectedValueOnce(new Error('Collections index unavailable'));
    const { result } = renderHook(() => useSearchResults(), { wrapper });
    await waitFor(() => {
      expect(result.current.error).toBe('Collections index unavailable');
    });
  });
});
