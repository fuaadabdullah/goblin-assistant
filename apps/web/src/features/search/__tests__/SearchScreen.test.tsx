import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

const mockUseSearchResults = jest.fn();
const mockSearchView = jest.fn();

jest.mock('../hooks/useSearchResults', () => ({
  useSearchResults: () => mockUseSearchResults(),
}));

jest.mock('../components/SearchView', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    mockSearchView(props);
    return <div data-testid="search-view" />;
  },
}));

import SearchScreen from '../SearchScreen';

describe('SearchScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
      setQuery: jest.fn(),
      setScope: jest.fn(),
      setSelectedCollection: jest.fn(),
      handleSearch: jest.fn(),
      handleQuickQuery: jest.fn(),
      handleClear: jest.fn(),
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
      setQuery: jest.fn(),
      setScope: jest.fn(),
      setSelectedCollection: jest.fn(),
      handleSearch: jest.fn(),
      handleQuickQuery: jest.fn(),
      handleClear: jest.fn(),
    };
    mockUseSearchResults.mockReturnValue(state);

    render(<SearchScreen />);

    expect(mockSearchView).toHaveBeenCalledWith(expect.objectContaining({ state }));
  });
});
