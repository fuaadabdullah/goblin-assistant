import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SandboxPage from '../SandboxPage';

jest.mock('@/features/sandbox/SandboxScreen', () => function MockSandboxScreen() {
  return <div data-testid="sandbox-screen">Sandbox Screen</div>;
});

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
