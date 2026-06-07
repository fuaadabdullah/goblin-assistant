import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('next/link', () => ({
  default: function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  },
}));

import ChatHeader from '../ChatHeader';

describe('ChatHeader', () => {
  const defaultProps = {
    isAdmin: false,
    onClear: vi.fn(),
  };

  beforeEach(() => vi.clearAllMocks());

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
    expect(screen.queryByLabelText(/chat panel/i)).not.toBeInTheDocument();
  });

  it('shows unified mobile panel toggle when enabled', () => {
    const onToggle = vi.fn();
    render(<ChatHeader {...defaultProps} showMobilePanelToggle onToggleMobilePanel={onToggle} />);
    const btn = screen.getByLabelText('Open chat panel');
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveTextContent('Conversations');
  });

  it('toggles unified mobile panel on click', () => {
    const onToggle = vi.fn();
    render(<ChatHeader {...defaultProps} showMobilePanelToggle onToggleMobilePanel={onToggle} />);
    fireEvent.click(screen.getByLabelText('Open chat panel'));
    expect(onToggle).toHaveBeenCalled();
  });

  it('shows close label when mobile panel is open', () => {
    render(
      <ChatHeader
        {...defaultProps}
        showMobilePanelToggle
        onToggleMobilePanel={vi.fn()}
        isMobilePanelOpen
      />
    );
    expect(screen.getByLabelText('Close chat panel')).toBeInTheDocument();
  });

  it('sets aria-expanded correctly', () => {
    const { rerender } = render(
      <ChatHeader
        {...defaultProps}
        showMobilePanelToggle
        onToggleMobilePanel={vi.fn()}
        isMobilePanelOpen={false}
      />
    );
    expect(screen.getByLabelText('Open chat panel')).toHaveAttribute('aria-expanded', 'false');
    rerender(
      <ChatHeader
        {...defaultProps}
        showMobilePanelToggle
        onToggleMobilePanel={vi.fn()}
        isMobilePanelOpen
      />
    );
    expect(screen.getByLabelText('Close chat panel')).toHaveAttribute('aria-expanded', 'true');
  });

  it('shows active preview tab label in the toggle', () => {
    render(
      <ChatHeader
        {...defaultProps}
        showMobilePanelToggle
        onToggleMobilePanel={vi.fn()}
        activeMobilePanelTab="preview"
      />
    );
    expect(screen.getByLabelText('Open chat panel')).toHaveTextContent('Preview');
  });
});
