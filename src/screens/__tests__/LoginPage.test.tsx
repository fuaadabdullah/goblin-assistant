import { fireEvent, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import LoginPage from '../LoginPage';

const pushMock = jest.fn();
let query: Record<string, unknown> = {};

jest.mock('next/router', () => ({
  useRouter: () => ({
    query,
    push: pushMock,
  }),
}));

jest.mock('../../components/Auth/ModularLoginForm', () => ({
  __esModule: true,
  default: ({ onSuccess }: { onSuccess: () => void }) => (
    <button type="button" onClick={onSuccess}>
      complete-login
    </button>
  ),
}));

jest.mock('../../components/Seo', () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock('next/link', () => ({
  __esModule: true,
  default: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

describe('LoginPage redirects', () => {
  beforeEach(() => {
    query = {};
    pushMock.mockClear();
  });

  it('prefers redirect over from', () => {
    query = { redirect: '/chat?tab=history', from: '/account' };

    render(<LoginPage />);
    fireEvent.click(screen.getByRole('button', { name: 'complete-login' }));

    expect(pushMock).toHaveBeenCalledWith('/chat?tab=history');
  });

  it('falls back to from when redirect is absent', () => {
    query = { from: '/account' };

    render(<LoginPage />);
    fireEvent.click(screen.getByRole('button', { name: 'complete-login' }));

    expect(pushMock).toHaveBeenCalledWith('/account');
  });

  it('rejects unsafe redirect values', () => {
    query = { redirect: 'https://evil.example/path', from: '/chat' };

    render(<LoginPage />);
    fireEvent.click(screen.getByRole('button', { name: 'complete-login' }));

    expect(pushMock).toHaveBeenCalledWith('/chat');
  });

  it('falls back to root when redirect inputs are unsafe', () => {
    query = { redirect: '//evil.example', from: 'https://evil.example' };

    render(<LoginPage />);
    fireEvent.click(screen.getByRole('button', { name: 'complete-login' }));

    expect(pushMock).toHaveBeenCalledWith('/');
  });
});
