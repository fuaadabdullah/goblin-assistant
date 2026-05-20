import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('next/link', () => function MockLink({ children, href, ...rest }: { children: React.ReactNode; href: string; [key: string]: unknown }) {
  return <a href={href} {...rest}>{children}</a>;
});

import ChatSidebar from '../ChatSidebar';
import type { ChatThread } from '../../types';

const mockThreads: ChatThread[] = [
  {
    id: 'conv-1',
    threadKey: 'backend:conv-1',
    title: 'First Chat',
    snippet: 'Hello there!',
    createdAt: '2024-01-01T00:00:00Z',
    updatedAt: '2024-01-01T01:00:00Z',
    source: 'backend',
  },
  {
    id: 'conv-2',
    threadKey: 'backend:conv-2',
    title: 'Second Chat',
    snippet: 'Goodbye!',
    createdAt: '2024-01-02T00:00:00Z',
    updatedAt: '2024-01-02T01:00:00Z',
    source: 'backend',
  },
];

describe('ChatSidebar', () => {
  const defaultProps = {
    threads: mockThreads,
    isThreadsLoading: false,
    activeThreadKey: null,
    onSelectThread: jest.fn(),
    onNewConversation: jest.fn(),
    isAdmin: false,
    totalTokens: 0,
    messageCount: 0,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders Conversations heading and New Conversation button', () => {
    render(<ChatSidebar {...defaultProps} />);
    expect(screen.getByText('Conversations')).toBeInTheDocument();
    expect(screen.getByText('New Conversation')).toBeInTheDocument();
  });

  it('calls onNewConversation when button is clicked', () => {
    render(<ChatSidebar {...defaultProps} />);
    fireEvent.click(screen.getByText('New Conversation'));
    expect(defaultProps.onNewConversation).toHaveBeenCalled();
  });

  it('renders thread list', () => {
    render(<ChatSidebar {...defaultProps} />);
    expect(screen.getByText('First Chat')).toBeInTheDocument();
    expect(screen.getByText('Hello there!')).toBeInTheDocument();
    expect(screen.getByText('Second Chat')).toBeInTheDocument();
  });

  it('calls onSelectThread when a thread is clicked', () => {
    render(<ChatSidebar {...defaultProps} />);
    fireEvent.click(screen.getByText('First Chat'));
    expect(defaultProps.onSelectThread).toHaveBeenCalledWith('backend:conv-1');
  });

  it('shows Active badge for selected thread', () => {
    render(<ChatSidebar {...defaultProps} activeThreadKey="backend:conv-1" messageCount={5} />);
    expect(screen.getByText('Active')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('shows loading skeleton when isThreadsLoading', () => {
    render(<ChatSidebar {...defaultProps} isThreadsLoading={true} threads={[]} />);
    // Should show animation skeleton, not thread list
    expect(screen.queryByText('First Chat')).not.toBeInTheDocument();
  });

  it('shows empty state when no threads', () => {
    render(<ChatSidebar {...defaultProps} threads={[]} />);
    expect(screen.getByText(/start a conversation/i)).toBeInTheDocument();
  });

  it('shows helpful tips section', () => {
    render(<ChatSidebar {...defaultProps} />);
    expect(screen.getByText('Helpful Tips')).toBeInTheDocument();
  });

  it('shows admin stats when isAdmin is true', () => {
    render(<ChatSidebar {...defaultProps} isAdmin={true} totalTokens={1500} messageCount={10} />);
    expect(screen.getByText('Total Tokens')).toBeInTheDocument();
    expect(screen.getByText('1500')).toBeInTheDocument();
    expect(screen.getByText('View admin logs')).toBeInTheDocument();
  });

  it('hides admin stats when isAdmin is false', () => {
    render(<ChatSidebar {...defaultProps} isAdmin={false} />);
    expect(screen.queryByText('Total Tokens')).not.toBeInTheDocument();
  });

  it('applies className prop', () => {
    const { container } = render(<ChatSidebar {...defaultProps} className="test-class" />);
    expect(container.firstChild).toHaveClass('test-class');
  });
});
