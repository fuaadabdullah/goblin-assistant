import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

const mockUseAuthSession = jest.fn();
const mockUseChatSession = jest.fn();
const mockIsAdminUser = jest.fn();
const mockChatView = jest.fn();

jest.mock('../../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => mockUseAuthSession(),
}));

jest.mock('../hooks/useChatSession', () => ({
  useChatSession: () => mockUseChatSession(),
}));

jest.mock('../../../utils/access', () => ({
  isAdminUser: (...args: unknown[]) => mockIsAdminUser(...args),
}));

jest.mock('../components/ChatView', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    mockChatView(props);
    return <div data-testid="chat-view" data-admin={String(props.isAdmin)} />;
  },
}));

import ChatScreen from '../ChatScreen';

describe('ChatScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseAuthSession.mockReturnValue({ user: { email: 'admin@goblin.dev' } });
    mockUseChatSession.mockReturnValue({ messages: [], input: '' });
    mockIsAdminUser.mockReturnValue(true);
  });

  it('passes session state to ChatView', () => {
    const session = { messages: [{ id: '1', content: 'hello' }], input: 'test' };
    mockUseChatSession.mockReturnValue(session);

    render(<ChatScreen />);

    expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    expect(mockChatView).toHaveBeenCalledWith(expect.objectContaining({ session, isAdmin: true }));
  });

  it('derives admin access from auth user', () => {
    const user = { email: 'user@example.com', role: 'owner' };
    mockUseAuthSession.mockReturnValue({ user });
    mockIsAdminUser.mockReturnValue(false);

    render(<ChatScreen />);

    expect(mockIsAdminUser).toHaveBeenCalledWith(user);
    expect(screen.getByTestId('chat-view')).toHaveAttribute('data-admin', 'false');
  });

  it('handles missing user by passing non-admin', () => {
    mockUseAuthSession.mockReturnValue({ user: null });
    mockIsAdminUser.mockReturnValue(false);

    render(<ChatScreen />);

    expect(mockIsAdminUser).toHaveBeenCalledWith(null);
    expect(mockChatView).toHaveBeenCalledWith(
      expect.objectContaining({
        isAdmin: false,
      })
    );
  });
});
