import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('../../../../../src/layout/AdminLayout', () => {
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

jest.mock('../../../../../src/components/RouteBoundary', () => ({
  withRouteErrorBoundary: (Component: React.ComponentType, _name: string) => Component,
}));

jest.mock('../../../../../src/features/admin/kpi/KpiDashboard', () => {
  return function MockKpiDashboard() {
    return <div data-testid="kpi-dashboard" />;
  };
});

import KpiPage from '../../../../../app/admin/kpi/page';

describe('admin KPI page', () => {
  it('renders the KPI dashboard inside the admin layout', () => {
    render(<KpiPage />);

    expect(screen.getByRole('main', { name: 'KPI Dashboard' })).toBeInTheDocument();
    expect(screen.getByTestId('kpi-dashboard')).toBeInTheDocument();
  });
});
