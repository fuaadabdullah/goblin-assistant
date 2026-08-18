import React from 'react';
import { render, screen } from '@testing-library/react';
import ChatPage from '../ChatPage';

vi.mock('@/features/chat/ChatScreen', () => ({
  default: function MockChatScreen() {
    return <div data-testid="chat-screen">Chat Screen</div>;
  },
}));

describe('ChatPage', () => {
  it('renders ChatScreen component', () => {
    render(<ChatPage />);
    expect(screen.getByTestId('chat-screen')).toBeInTheDocument();
  });

  it('displays chat screen content', () => {
    render(<ChatPage />);
    expect(screen.getByText('Chat Screen')).toBeInTheDocument();
  });

  it('has correct page structure', () => {
    const { container } = render(<ChatPage />);
    expect(container.firstChild).toBeInTheDocument();
  });
});
