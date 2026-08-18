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

jest.mock('@/features/admin/pilot/PilotKitScreen', () => {
  return function MockPilotKitScreen() {
    return <div data-testid="pilot-kit" />;
  };
});

import PilotPage from '../../../../../app/admin/pilot/page';

describe('admin pilot page', () => {
  it('renders the pilot kit inside the admin layout', () => {
    render(<PilotPage />);

    expect(screen.getByRole('main', { name: 'Pilot Kit' })).toBeInTheDocument();
    expect(screen.getByTestId('pilot-kit')).toBeInTheDocument();
  });
});
