import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/sandbox',
}));

vi.mock('../../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => ({ isAuthenticated: true }),
}));

const mockSession = { code: '', output: '', run: vi.fn() };
vi.mock('../hooks/useSandboxSession', () => ({
  useSandboxSession: () => mockSession,
}));

vi.mock('../../../components/auth/AuthPrompt', () => ({
  default: function MockAuthPrompt(props: { onClose: () => void }) {
    return (
      <div data-testid="auth-prompt">
        <button onClick={props.onClose}>close</button>
      </div>
    );
  },
}));

vi.mock('../components/SandboxView', () => ({
  default: function MockSandboxView(props: { isGuest: boolean; onRequireAuth: () => boolean }) {
    return (
      <div data-testid="sandbox-view" data-guest={String(props.isGuest)}>
        <button data-testid="require-auth" onClick={() => props.onRequireAuth()}>
          auth
        </button>
      </div>
    );
  },
}));

import SandboxScreen from '../SandboxScreen';

describe('SandboxScreen', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders SandboxView', () => {
    render(<SandboxScreen />);
    expect(screen.getByTestId('sandbox-view')).toBeInTheDocument();
  });

  it('isGuest is false when authenticated', () => {
    render(<SandboxScreen />);
    expect(screen.getByTestId('sandbox-view').getAttribute('data-guest')).toBe('false');
  });

  it('does not show auth prompt initially', () => {
    render(<SandboxScreen />);
    expect(screen.queryByTestId('auth-prompt')).not.toBeInTheDocument();
  });
});
