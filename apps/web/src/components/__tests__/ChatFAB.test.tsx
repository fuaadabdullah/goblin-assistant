import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

const { pushMock, setChatSidebarOpenMock, trackEventMock, pathnameMock } = vi.hoisted(() => ({
  pushMock: vi.fn().mockResolvedValue(undefined),
  setChatSidebarOpenMock: vi.fn(),
  trackEventMock: vi.fn(),
  pathnameMock: vi.fn().mockReturnValue('/'),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
  usePathname: () => pathnameMock(),
}));

vi.mock('../../store/uiStore', () => ({
  useUIStore: (
    selector: (state: { setChatSidebarOpen: typeof setChatSidebarOpenMock }) => unknown
  ) => selector({ setChatSidebarOpen: setChatSidebarOpenMock }),
}));

vi.mock('../../utils/analytics', () => ({
  trackEvent: trackEventMock,
}));

import ChatFAB from '../ChatFAB';

describe('ChatFAB', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pathnameMock.mockReturnValue('/');
    pushMock.mockResolvedValue(undefined);
  });

  it('navigates to chat, tracks the click, and opens the drawer', async () => {
    render(<ChatFAB />);

    fireEvent.click(screen.getByRole('button', { name: 'Open Chat' }));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith('/chat'));
    expect(trackEventMock).toHaveBeenCalledWith('chat_fab_clicked');
    expect(setChatSidebarOpenMock).toHaveBeenCalledWith(true);
  });

  it('still opens chat when navigation rejects', async () => {
    pushMock.mockRejectedValueOnce(new Error('navigation failed'));

    render(<ChatFAB />);
    fireEvent.click(screen.getByRole('button', { name: 'Open Chat' }));

    await waitFor(() => expect(trackEventMock).toHaveBeenCalledWith('chat_fab_clicked'));
    expect(setChatSidebarOpenMock).toHaveBeenCalledWith(true);
  });

  it('renders nothing on /chat so it cannot cover the composer Send button', () => {
    pathnameMock.mockReturnValue('/chat');

    render(<ChatFAB />);

    expect(screen.queryByRole('button', { name: 'Open Chat' })).not.toBeInTheDocument();
  });
});
