import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ChatPage from '../ChatPage';

jest.mock(
  '@/features/chat/ChatScreen',
  () =>
    function MockChatScreen() {
      return <div data-testid="chat-screen">Chat Screen</div>;
    }
);

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
