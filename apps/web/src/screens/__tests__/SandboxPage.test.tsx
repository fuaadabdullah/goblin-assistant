import React from 'react';
import { render, screen } from '@testing-library/react';

// SandboxPage uses next/dynamic, so we mock next/dynamic to render synchronously
vi.mock('next/dynamic', () => ({
  default: function mockDynamic(importFn: () => Promise<{ default: React.ComponentType }>) {
    const MockDynamic = function () {
      return React.createElement('div', { 'data-testid': 'sandbox-screen' }, 'Sandbox Screen');
    };
    MockDynamic.displayName = 'DynamicSandboxScreen';
    return MockDynamic;
  },
}));

// Also mock the features module in case it is resolved directly
vi.mock('@/features/sandbox/SandboxScreen', () => ({
  default: function MockSandboxScreen() {
    return <div data-testid="sandbox-screen">Sandbox Screen</div>;
  },
}));

vi.mock('../../features/sandbox/components/SandboxSkeleton', () => ({
  default: function MockSandboxSkeleton() {
    return <div data-testid="sandbox-skeleton" />;
  },
}));

import SandboxPage from '../SandboxPage';

describe('SandboxPage', () => {
  it('renders SandboxScreen component', () => {
    render(<SandboxPage />);
    expect(screen.getByTestId('sandbox-screen')).toBeInTheDocument();
  });

  it('displays sandbox content', () => {
    render(<SandboxPage />);
    expect(screen.getByText('Sandbox Screen')).toBeInTheDocument();
  });

  it('has correct structure', () => {
    const { container } = render(<SandboxPage />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
