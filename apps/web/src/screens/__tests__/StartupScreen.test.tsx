import React from 'react';
import { render, screen } from '@testing-library/react';

const mockReplace = vi.fn().mockResolvedValue(true);
const mockPrefetch = vi.fn().mockResolvedValue(undefined);
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    replace: mockReplace,
    prefetch: mockPrefetch,
    push: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => '/startup',
  useSearchParams: () => new URLSearchParams(),
}));

let mockStartupReturn = {
  status: 'loading' as string,
  message: 'Initializing...',
  destinationRoute: null as string | null,
};
vi.mock('../../features/startup/hooks/useStartupFlow', () => ({
  useStartupFlow: () => mockStartupReturn,
}));

vi.mock('../../features/startup/components/GoblinBootScreen', () => ({
  default: function MockBootScreen(props: { status: string; message: string }) {
    return (
      <div data-testid="boot-screen" data-status={props.status}>
        {props.message}
      </div>
    );
  },
}));

import StartupScreen from '../StartupScreen';

describe('StartupScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStartupReturn = { status: 'loading', message: 'Initializing...', destinationRoute: null };
  });

  it('renders boot screen', () => {
    render(<StartupScreen />);
    expect(screen.getByTestId('boot-screen')).toBeInTheDocument();
  });

  it('passes status and message', () => {
    render(<StartupScreen />);
    expect(screen.getByTestId('boot-screen')).toHaveAttribute('data-status', 'loading');
    expect(screen.getByText('Initializing...')).toBeInTheDocument();
  });

  it('prefetches destination when available', () => {
    mockStartupReturn = { status: 'loading', message: 'Almost ready', destinationRoute: '/chat' };
    render(<StartupScreen />);
    expect(mockPrefetch).toHaveBeenCalledWith('/chat');
  });

  it('redirects when status is ready', () => {
    mockStartupReturn = { status: 'ready', message: 'Done', destinationRoute: '/chat' };
    render(<StartupScreen />);
    expect(mockReplace).toHaveBeenCalledWith('/chat');
  });

  it('redirects on error with destination', () => {
    mockStartupReturn = {
      status: 'error',
      message: 'Failed',
      destinationRoute: '/help?reason=startup_failed',
    };
    render(<StartupScreen />);
    expect(mockReplace).toHaveBeenCalledWith('/help?reason=startup_failed');
  });
});
