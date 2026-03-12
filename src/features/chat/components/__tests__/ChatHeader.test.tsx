import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

jest.mock('lucide-react', () => new Proxy({}, {
  get: (_, name) => {
    if (name === '__esModule') return true;
    return (props: Record<string, unknown>) => <span data-testid={`icon-${String(name)}`} {...props} />;
  },
}));
jest.mock('next/link', () => function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
  return <a href={href}>{children}</a>;
});

import ChatHeader from '../ChatHeader';

describe('ChatHeader', () => {
  const defaultProps = {
    isAdmin: false,
    onClear: jest.fn(),
  };

  beforeEach(() => jest.clearAllMocks());

  it('renders the title', () => {
    render(<ChatHeader {...defaultProps} />);
    expect(screen.getByText('AI Orchestration Console')).toBeInTheDocument();
  });

  it('shows Live gateway badge', () => {
    render(<ChatHeader {...defaultProps} />);
    expect(screen.getByText('Live gateway')).toBeInTheDocument();
  });

  it('renders Clear Chat button', () => {
    render(<ChatHeader {...defaultProps} />);
    expect(screen.getByText('Clear Chat')).toBeInTheDocument();
  });

  it('calls onClear when clicked', () => {
    render(<ChatHeader {...defaultProps} />);
    fireEvent.click(screen.getByText('Clear Chat'));
    expect(defaultProps.onClear).toHaveBeenCalled();
  });

  it('renders Global Search link', () => {
    render(<ChatHeader {...defaultProps} />);
    const link = screen.getByText('Global Search');
    expect(link.closest('a')).toHaveAttribute('href', '/search');
  });

  it('does not show Admin Dashboard for non-admin', () => {
    render(<ChatHeader {...defaultProps} />);
    expect(screen.queryByText('Admin Dashboard')).not.toBeInTheDocument();
  });

  it('shows Admin Dashboard for admin', () => {
    render(<ChatHeader {...defaultProps} isAdmin />);
    const link = screen.getByText('Admin Dashboard');
    expect(link.closest('a')).toHaveAttribute('href', '/admin');
  });

  it('does not show sidebar toggle by default', () => {
    render(<ChatHeader {...defaultProps} />);
    expect(screen.queryByLabelText(/conversations/i)).not.toBeInTheDocument();
  });

  it('shows sidebar toggle when enabled', () => {
    const onToggle = jest.fn();
    render(<ChatHeader {...defaultProps} showSidebarToggle onToggleSidebar={onToggle} />);
    const btn = screen.getByLabelText('Open conversations');
    expect(btn).toBeInTheDocument();
  });

  it('toggles sidebar on click', () => {
    const onToggle = jest.fn();
    render(<ChatHeader {...defaultProps} showSidebarToggle onToggleSidebar={onToggle} />);
    fireEvent.click(screen.getByLabelText('Open conversations'));
    expect(onToggle).toHaveBeenCalled();
  });

  it('shows close label when sidebar is open', () => {
    render(<ChatHeader {...defaultProps} showSidebarToggle onToggleSidebar={jest.fn()} isSidebarOpen />);
    expect(screen.getByLabelText('Close conversations')).toBeInTheDocument();
  });

  it('sets aria-expanded correctly', () => {
    const { rerender } = render(<ChatHeader {...defaultProps} showSidebarToggle onToggleSidebar={jest.fn()} isSidebarOpen={false} />);
    expect(screen.getByLabelText('Open conversations')).toHaveAttribute('aria-expanded', 'false');
    rerender(<ChatHeader {...defaultProps} showSidebarToggle onToggleSidebar={jest.fn()} isSidebarOpen />);
    expect(screen.getByLabelText('Close conversations')).toHaveAttribute('aria-expanded', 'true');
  });
});
