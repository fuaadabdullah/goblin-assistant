import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('../../../../components/TwoColumnLayout', () => {
  return function MockTwoColumnLayout({ children, sidebar }: { children: React.ReactNode; sidebar: React.ReactNode }) {
    return <div data-testid="two-col"><div data-testid="sidebar">{sidebar}</div><div data-testid="main">{children}</div></div>;
  };
});

import SandboxSkeleton from '../SandboxSkeleton';

describe('SandboxSkeleton', () => {
  it('renders without error', () => {
    const { container } = render(<SandboxSkeleton />);
    expect(container.firstChild).toBeTruthy();
  });

  it('renders two-column layout', () => {
    render(<SandboxSkeleton />);
    expect(screen.getByTestId('two-col')).toBeInTheDocument();
  });

  it('renders sidebar skeleton blocks', () => {
    render(<SandboxSkeleton />);
    const sidebar = screen.getByTestId('sidebar');
    expect(sidebar.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });

  it('renders main skeleton blocks', () => {
    render(<SandboxSkeleton />);
    const main = screen.getByTestId('main');
    expect(main.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
  });
});
