import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import EnhancedProvidersPage from '../EnhancedProvidersPage';

jest.mock(
  '@/features/admin/providers/ProvidersManagerScreen',
  () =>
    function MockScreen() {
      return <div data-testid="enhanced-providers-screen">Enhanced Providers</div>;
    }
);

describe('EnhancedProvidersPage', () => {
  it('renders EnhancedProvidersScreen component', () => {
    render(<EnhancedProvidersPage />);
    expect(screen.getByTestId('enhanced-providers-screen')).toBeInTheDocument();
  });

  it('displays providers content', () => {
    render(<EnhancedProvidersPage />);
    expect(screen.getByText('Enhanced Providers')).toBeInTheDocument();
  });

  it('has proper page structure', () => {
    const { container } = render(<EnhancedProvidersPage />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
