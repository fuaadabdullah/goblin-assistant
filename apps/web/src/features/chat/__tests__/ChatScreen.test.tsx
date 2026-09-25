import React from 'react';
import { render, screen } from '@testing-library/react';

const mockUseAuthSession = vi.fn();
const mockUseChatSession = vi.fn();
const mockChatView = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/chat',
}));

vi.mock('../../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => mockUseAuthSession(),
}));

vi.mock('../hooks/useChatSession', () => ({
  useChatSession: () => mockUseChatSession(),
}));

vi.mock('../components/ChatView', () => ({
  __esModule: true,
  default: (props: Record<string, unknown>) => {
    mockChatView(props);
    return <div data-testid="chat-view" data-admin={String(props.isAdmin)} />;
  },
}));

import ChatScreen from '../ChatScreen';

describe('ChatScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuthSession.mockReturnValue({ isAuthenticated: true, isAdmin: true });
    mockUseChatSession.mockReturnValue({ messages: [], input: '' });
  });

  it('passes session state to ChatView', () => {
    const session = { messages: [{ id: '1', content: 'hello' }], input: 'test' };
    mockUseChatSession.mockReturnValue(session);

    render(<ChatScreen />);

    expect(screen.getByTestId('chat-view')).toBeInTheDocument();
    expect(mockChatView).toHaveBeenCalledWith(expect.objectContaining({ session, isAdmin: true }));
  });

  it('forwards the server-derived admin claim from the auth session', () => {
    mockUseAuthSession.mockReturnValue({ isAuthenticated: true, isAdmin: false });

    render(<ChatScreen />);

    expect(screen.getByTestId('chat-view')).toHaveAttribute('data-admin', 'false');
    expect(mockChatView).toHaveBeenCalledWith(
      expect.objectContaining({
        isAdmin: false,
      })
    );
  });
});
