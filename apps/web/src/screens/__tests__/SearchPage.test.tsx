import React from 'react';
import { render, screen } from '@testing-library/react';
import SearchPage from '../SearchPage';

vi.mock(
  '@/features/search/SearchScreen',
  () => ({
    default: function MockSearchScreen() {
      return <div data-testid="search-screen">Search Screen</div>;
    },
  })
);

describe('SearchPage', () => {
  it('renders SearchScreen component', () => {
    render(<SearchPage />);
    expect(screen.getByTestId('search-screen')).toBeInTheDocument();
  });

  it('displays search content', () => {
    render(<SearchPage />);
    expect(screen.getByText('Search Screen')).toBeInTheDocument();
  });

  it('has correct structure', () => {
    const { container } = render(<SearchPage />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
