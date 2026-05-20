import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SearchEmptyState from '../SearchEmptyState';

describe('SearchEmptyState', () => {
  it('renders the icon', () => {
    render(<SearchEmptyState icon="🔍" title="No results" description="Try another query." />);
    expect(screen.getByText('🔍')).toBeInTheDocument();
  });

  it('renders the title', () => {
    render(<SearchEmptyState icon="🔍" title="No results" description="Try again." />);
    expect(screen.getByText('No results')).toBeInTheDocument();
  });

  it('renders the description', () => {
    render(<SearchEmptyState icon="🔍" title="No results" description="Try another query." />);
    expect(screen.getByText('Try another query.')).toBeInTheDocument();
  });

  it('renders heading element', () => {
    render(<SearchEmptyState icon="🔍" title="Empty" description="Desc" />);
    expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Empty');
  });
});
