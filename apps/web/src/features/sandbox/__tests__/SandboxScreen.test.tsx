import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

const mockPush = jest.fn();
jest.mock('next/router', () => ({
  useRouter: () => ({
    isReady: true,
    query: {},
    push: mockPush,
    asPath: '/sandbox',
    pathname: '/sandbox',
    events: { on: jest.fn(), off: jest.fn() },
  }),
}));

jest.mock('../../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => ({ isAuthenticated: true }),
}));

const mockSession = { code: '', output: '', run: jest.fn() };
jest.mock('../hooks/useSandboxSession', () => ({
  useSandboxSession: () => mockSession,
}));

jest.mock('../../../components/auth/AuthPrompt', () => {
  return function MockAuthPrompt(props: { onClose: () => void }) {
    return <div data-testid="auth-prompt"><button onClick={props.onClose}>close</button></div>;
  };
});

jest.mock('../components/SandboxView', () => {
  return function MockSandboxView(props: { isGuest: boolean; onRequireAuth: () => boolean }) {
    return (
      <div data-testid="sandbox-view" data-guest={String(props.isGuest)}>
        <button data-testid="require-auth" onClick={() => props.onRequireAuth()}>auth</button>
      </div>
    );
  };
});

import SandboxScreen from '../SandboxScreen';

describe('SandboxScreen', () => {
  beforeEach(() => jest.clearAllMocks());

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
