import React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('../SearchHeader', () => function MockSearchHeader({ title }: { title: string }) {
  return <div data-testid="search-header">{title}</div>;
});
jest.mock('../SearchQuickQueries', () => function MockQuickQueries() {
  return <div data-testid="search-quick-queries" />;
});
jest.mock('../SearchForm', () => function MockSearchForm() {
  return <div data-testid="search-form" />;
});
jest.mock('../SearchResultsList', () => function MockResults() {
  return <div data-testid="search-results-list" />;
});
jest.mock('../SearchEmptyState', () => function MockEmptyState({ title }: { title: string }) {
  return <div data-testid="search-empty-state">{title}</div>;
});
jest.mock('../../../../components/Seo', () => function MockSeo() {
  return null;
});

import SearchView from '../SearchView';
import type { SearchState } from '../../../search/hooks/useSearchResults';
import type { RefObject } from 'react';

function makeState(overrides: Partial<SearchState> = {}): SearchState {
  return {
    query: '',
    results: [],
    error: null,
    selectedCollection: '',
    scope: 'documents' as SearchState['scope'],
    quickQueries: ['q1'],
    searching: false,
    collectionsLoading: false,
    collectionsData: [],
    queryRef: { current: null } as RefObject<HTMLInputElement>,
    setQuery: jest.fn(),
    setScope: jest.fn(),
    setSelectedCollection: jest.fn(),
    handleSearch: jest.fn(),
    handleQuickQuery: jest.fn(),
    handleClear: jest.fn(),
    ...overrides,
  };
}

describe('SearchView', () => {
  it('renders search header', () => {
    render(<SearchView state={makeState()} />);
    expect(screen.getByTestId('search-header')).toHaveTextContent('Gateway Audit Log');
  });

  it('renders search form', () => {
    render(<SearchView state={makeState()} />);
    expect(screen.getByTestId('search-form')).toBeInTheDocument();
  });

  it('renders quick queries', () => {
    render(<SearchView state={makeState()} />);
    expect(screen.getByTestId('search-quick-queries')).toBeInTheDocument();
  });

  it('shows empty state when no query entered', () => {
    render(<SearchView state={makeState()} />);
    expect(screen.getByTestId('search-empty-state')).toHaveTextContent('Search everything');
  });

  it('shows no-results empty state with query but no results', () => {
    render(<SearchView state={makeState({ query: 'test', results: [] })} />);
    expect(screen.getByTestId('search-empty-state')).toHaveTextContent('No results found');
  });

  it('shows error when error is set', () => {
    render(<SearchView state={makeState({ error: 'Something broke' })} />);
    expect(screen.getByText('Something broke')).toBeInTheDocument();
  });

  it('shows results list when results are present', () => {
    const results = [{ id: '1', content: 'test', score: 0.9, metadata: {} }] as SearchState['results'];
    render(<SearchView state={makeState({ query: 'test', results })} />);
    expect(screen.getByTestId('search-results-list')).toBeInTheDocument();
  });

  it('does not show empty state when searching', () => {
    render(<SearchView state={makeState({ searching: true })} />);
    expect(screen.queryByTestId('search-empty-state')).not.toBeInTheDocument();
  });

  it('has accessible main landmark', () => {
    render(<SearchView state={makeState()} />);
    expect(screen.getByRole('main')).toHaveAttribute('aria-label', 'Search');
  });
});
