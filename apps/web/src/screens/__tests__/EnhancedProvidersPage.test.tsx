import React from 'react';
import { render, screen } from '@testing-library/react';
import EnhancedProvidersPage from '../EnhancedProvidersPage';

vi.mock(
  '@/features/admin/providers/ProvidersManagerScreen',
  () => ({
    default: function MockScreen() {
      return <div data-testid="enhanced-providers-screen">Enhanced Providers</div>;
    },
  })
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
