import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('../../ui/Button', () => {
  return function MockButton({ children, onClick, disabled, variant }: { children: React.ReactNode; onClick?: () => void; disabled?: boolean; variant?: string }) {
    return <button onClick={onClick} disabled={disabled} data-variant={variant}>{children}</button>;
  };
});

import { DashboardHeader } from '../DashboardHeader';

describe('DashboardHeader', () => {
  const defaultProps = {
    onRefresh: jest.fn(),
    autoRefresh: false,
    onToggleAutoRefresh: jest.fn(),
    loading: false,
  };

  beforeEach(() => jest.clearAllMocks());

  it('renders the welcome heading', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText('Welcome')).toBeInTheDocument();
  });

  it('renders the description', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText(/Start a chat/)).toBeInTheDocument();
  });

  it('shows Refresh button', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText('Refresh')).toBeInTheDocument();
  });

  it('shows Refreshing... when loading', () => {
    render(<DashboardHeader {...defaultProps} loading={true} />);
    expect(screen.getByText('Refreshing...')).toBeInTheDocument();
  });

  it('calls onRefresh', () => {
    render(<DashboardHeader {...defaultProps} />);
    fireEvent.click(screen.getByText('Refresh'));
    expect(defaultProps.onRefresh).toHaveBeenCalled();
  });

  it('shows auto-refresh off by default', () => {
    render(<DashboardHeader {...defaultProps} />);
    expect(screen.getByText('Auto-refresh off')).toBeInTheDocument();
  });

  it('shows auto-refresh on when enabled', () => {
    render(<DashboardHeader {...defaultProps} autoRefresh={true} />);
    expect(screen.getByText('Auto-refresh on')).toBeInTheDocument();
  });

  it('calls onToggleAutoRefresh', () => {
    render(<DashboardHeader {...defaultProps} />);
    fireEvent.click(screen.getByText('Auto-refresh off'));
    expect(defaultProps.onToggleAutoRefresh).toHaveBeenCalled();
  });
});
