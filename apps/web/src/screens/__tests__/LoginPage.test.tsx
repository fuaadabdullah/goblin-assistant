import { fireEvent, render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';
import LoginPage, { resolveOauthErrorMessage } from '../LoginPage';

const pushMock = vi.fn();
let query: Record<string, string> = {};

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: pushMock, replace: vi.fn() }),
  useSearchParams: () => new URLSearchParams(query),
  usePathname: () => '/login',
}));

vi.mock('../../components/auth/ModularLoginForm', () => ({
  __esModule: true,
  default: ({ onSuccess }: { onSuccess: () => void }) => (
    <button type="button" onClick={onSuccess}>
      complete-login
    </button>
  ),
}));

vi.mock('../../components/Seo', () => ({
  __esModule: true,
  default: () => null,
}));

vi.mock('next/link', () => ({
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

describe('resolveOauthErrorMessage', () => {
  it('maps known oauth errors to user-friendly copy', () => {
    expect(resolveOauthErrorMessage('oauth_failed')).toBe('Google sign-in failed. Please try again.');
    expect(resolveOauthErrorMessage('no_code')).toBe(
      'Google sign-in did not return an authorization code.'
    );
    expect(resolveOauthErrorMessage('callback_failed')).toBe(
      'Google sign-in could not be completed. Try again.'
    );
  });

  it('keeps unknown oauth error codes visible', () => {
    expect(resolveOauthErrorMessage('invalid_scope')).toBe('Authentication error: invalid_scope');
  });
});
