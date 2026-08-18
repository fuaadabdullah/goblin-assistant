import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('@/layout/AdminLayout', () => {
  return function MockAdminLayout({
    children,
    mainId,
    mainLabel,
  }: {
    children: React.ReactNode;
    mainId: string;
    mainLabel: string;
  }) {
    return (
      <main id={mainId} aria-label={mainLabel}>
        {children}
      </main>
    );
  };
});

jest.mock('@/components/RouteBoundary', () => ({
  withRouteErrorBoundary: (Component: React.ComponentType, _name: string) => Component,
}));

jest.mock('@/features/admin/dogfood/DogfoodJournalScreen', () => {
  return function MockDogfoodJournalScreen() {
    return <div data-testid="dogfood-journal" />;
  };
});

import DogfoodPage from '../../../../../app/admin/dogfood/page';

describe('admin dogfood page', () => {
  it('renders the dogfood journal inside the admin layout', () => {
    render(<DogfoodPage />);

    expect(screen.getByRole('main', { name: 'Dogfood Journal' })).toBeInTheDocument();
    expect(screen.getByTestId('dogfood-journal')).toBeInTheDocument();
  });
});
