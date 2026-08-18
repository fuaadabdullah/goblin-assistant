import React from 'react';
import { render, screen } from '@testing-library/react';

const mockUseSearchResults = vi.fn();
const mockSearchView = vi.fn();

vi.mock('../hooks/useSearchResults', () => ({
  useSearchResults: () => mockUseSearchResults(),
}));

vi.mock('../components/SearchView', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    mockSearchView(props);
    return <div data-testid="search-view" />;
  },
}));

import SearchScreen from '../SearchScreen';

describe('SearchScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSearchResults.mockReturnValue({
      query: '',
      results: [],
      error: null,
      selectedCollection: '',
      scope: 'all',
      quickQueries: [],
      searching: false,
      collectionsLoading: false,
      collectionsData: [],
      queryRef: { current: null },
      setQuery: vi.fn(),
      setScope: vi.fn(),
      setSelectedCollection: vi.fn(),
      handleSearch: vi.fn(),
      handleQuickQuery: vi.fn(),
      handleClear: vi.fn(),
    });
  });

  it('renders SearchView', () => {
    render(<SearchScreen />);
    expect(screen.getByTestId('search-view')).toBeInTheDocument();
  });

  it('passes hook state to SearchView', () => {
    const state = {
      query: 'goblin',
      results: [{ id: '1', content: 'Goblin result', score: 0.95, metadata: {} }],
      error: null,
      selectedCollection: 'docs',
      scope: 'all',
      quickQueries: ['goblin'],
      searching: false,
      collectionsLoading: false,
      collectionsData: ['docs'],
      queryRef: { current: null },
      setQuery: vi.fn(),
      setScope: vi.fn(),
      setSelectedCollection: vi.fn(),
      handleSearch: vi.fn(),
      handleQuickQuery: vi.fn(),
      handleClear: vi.fn(),
    };
    mockUseSearchResults.mockReturnValue(state);

    render(<SearchScreen />);

    expect(mockSearchView).toHaveBeenCalledWith(expect.objectContaining({ state }));
  });
});
