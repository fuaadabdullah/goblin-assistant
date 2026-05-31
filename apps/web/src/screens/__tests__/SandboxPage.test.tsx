import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// SandboxPage uses next/dynamic, so we mock next/dynamic to render synchronously
jest.mock('next/dynamic', () => {
  return function mockDynamic(importFn: () => Promise<{ default: React.ComponentType }>) {
    // Return a synchronous placeholder that renders the mock set up below
    const MockDynamic = function () {
      return React.createElement('div', { 'data-testid': 'sandbox-screen' }, 'Sandbox Screen');
    };
    MockDynamic.displayName = 'DynamicSandboxScreen';
    return MockDynamic;
  };
});

// Also mock the features module in case it is resolved directly
jest.mock(
  '@/features/sandbox/SandboxScreen',
  () =>
    function MockSandboxScreen() {
      return <div data-testid="sandbox-screen">Sandbox Screen</div>;
    }
);

jest.mock('../../features/sandbox/components/SandboxSkeleton', () => {
  return function MockSandboxSkeleton() {
    return <div data-testid="sandbox-skeleton" />;
  };
});

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
