import React from 'react';
import { render, screen } from '@testing-library/react';

import SearchResultsList from '../SearchResultsList';

describe('SearchResultsList', () => {
  const makeResult = (overrides = {}) => ({
    id: '1',
    document: 'Test document content',
    ...overrides,
  });

  it('renders results count heading', () => {
    render(<SearchResultsList results={[makeResult()]} />);
    expect(screen.getByText('Search Results (1)')).toBeInTheDocument();
  });

  it('renders multiple results', () => {
    const results = [
      makeResult({ id: '1', document: 'First doc' }),
      makeResult({ id: '2', document: 'Second doc' }),
    ];
    render(<SearchResultsList results={results} />);
    expect(screen.getByText('First doc')).toBeInTheDocument();
    expect(screen.getByText('Second doc')).toBeInTheDocument();
  });

  it('shows result number labels', () => {
    const results = [makeResult({ id: '1' }), makeResult({ id: '2' })];
    render(<SearchResultsList results={results} />);
    expect(screen.getByText('Result 1')).toBeInTheDocument();
    expect(screen.getByText('Result 2')).toBeInTheDocument();
  });

  it('renders score when present', () => {
    render(<SearchResultsList results={[makeResult({ score: 0.9543 })]} />);
    expect(screen.getByText('Score: 0.9543')).toBeInTheDocument();
  });

  it('renders distance when present', () => {
    render(<SearchResultsList results={[makeResult({ distance: 0.1234 })]} />);
    expect(screen.getByText('Distance: 0.1234')).toBeInTheDocument();
  });

  it('renders metadata tags', () => {
    render(<SearchResultsList results={[makeResult({ metadata: { source: 'wiki', type: 'article' } })]} />);
    expect(screen.getByText('source: wiki')).toBeInTheDocument();
    expect(screen.getByText('type: article')).toBeInTheDocument();
  });

  it('does not render metadata section when metadata is empty', () => {
    render(<SearchResultsList results={[makeResult({ metadata: {} })]} />);
    expect(screen.queryByText(/source:/)).not.toBeInTheDocument();
  });

  it('handles empty results', () => {
    render(<SearchResultsList results={[]} />);
    expect(screen.getByText('Search Results (0)')).toBeInTheDocument();
  });
});
