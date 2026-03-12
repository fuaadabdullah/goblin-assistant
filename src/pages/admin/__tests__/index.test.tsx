import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('next/dynamic', () => {
  return function mockDynamic(loader: () => Promise<unknown>, opts?: { loading?: () => React.ReactElement }) {
    // Return the loading component for testing
    return function DynamicComponent() {
      if (opts?.loading) return opts.loading();
      return <div data-testid="dynamic">loaded</div>;
    };
  };
});

jest.mock('../../../layout/AdminLayout', () => {
  return function MockAdminLayout({ children, mainId, mainLabel }: { children: React.ReactNode; mainId: string; mainLabel: string }) {
    return <main id={mainId} aria-label={mainLabel}>{children}</main>;
  };
});

jest.mock('../../../components/RouteBoundary', () => ({
  withRouteErrorBoundary: (Component: React.ComponentType, _name: string) => Component,
}));

import Admin from '../index';

describe('Admin index page', () => {
  it('renders the admin layout', () => {
    render(<Admin />);
    expect(document.getElementById('main-content')).toBeInTheDocument();
  });

  it('has the admin dashboard label', () => {
    render(<Admin />);
    expect(screen.getByRole('main')).toHaveAttribute('aria-label', 'Admin Dashboard');
  });

  it('renders loading placeholder', () => {
    render(<Admin />);
    expect(screen.getByText('Loading dashboard...')).toBeInTheDocument();
  });
});
