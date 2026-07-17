import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { useEffect } from 'react';

const {
  mockSetQueryData,
  mockSignIn,
  mockSignUp,
  mockSignInWithOAuth,
  turnstileState,
  featureFlagsState,
} = vi.hoisted(() => ({
  mockSetQueryData: vi.fn(),
  mockSignIn: vi.fn(),
  mockSignUp: vi.fn(),
  mockSignInWithOAuth: vi.fn(),
  turnstileState: {
    enabled: false,
    token: '',
    siteKey: 'login-site',
  },
  featureFlagsState: {
    googleAuth: false,
  },
}));

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ setQueryData: mockSetQueryData }),
}));

vi.mock('@/lib/supabase', () => ({
  authSignUp: mockSignUp,
  authSignIn: mockSignIn,
  authSignInWithOAuth: mockSignInWithOAuth,
}));

vi.mock('../../../config/features', () => ({
  featureFlags: featureFlagsState,
}));

vi.mock('../../../config/turnstile', () => ({
  useTurnstile: () => ({
    enabled: turnstileState.enabled,
    token: turnstileState.token,
    siteKey: turnstileState.siteKey,
    reset: vi.fn(),
  }),
}));

vi.mock('../../../lib/query-keys', () => ({ queryKeys: { authValidate: ['auth'] } }));
vi.mock('@/utils/dev-log', () => ({ devError: vi.fn() }));
vi.mock('@/lib/error/toast', () => ({
  getUserMessage: (error: unknown) => (error instanceof Error ? error.message : String(error)),
}));

vi.mock('../LoginHeader', () => ({
  default: function MockLoginHeader({ isRegister }: { isRegister: boolean }) {
    return <div data-testid="login-header">{isRegister ? 'Register' : 'Login'}</div>;
  },
}));

vi.mock('../EmailPasswordForm', () => ({
  default: function MockEmailForm(props: { onSubmit?: (email: string, password: string) => void }) {
    return (
      <form
        data-testid="email-form"
        onSubmit={(event) => {
          event.preventDefault();
          props.onSubmit?.('test@test.com', 'pass');
        }}
      >
        <button type="submit">Submit</button>
      </form>
    );
  },
}));

vi.mock('../SocialLoginButtons', () => ({
  default: function MockSocialLoginButtons({
    onGoogleLogin,
  }: {
    onGoogleLogin: () => void;
    isLoading: boolean;
  }) {
    return (
      <button type="button" onClick={onGoogleLogin}>
        Google login
      </button>
    );
  },
}));

vi.mock('../Divider', () => ({
  default: function MockDivider() {
    return <hr data-testid="divider" />;
  },
}));

vi.mock('../PasskeyPanel', () => ({
  default: function MockPasskey() {
    return <div data-testid="passkey-panel" />;
  },
}));

vi.mock('../../TurnstileWidget', () => ({
  default: function MockTurnstile({ onVerify }: { onVerify: (token: string) => void }) {
    useEffect(() => {
      if (turnstileState.enabled && turnstileState.token) {
        onVerify(turnstileState.token);
      }
    }, [onVerify]);

    return <div data-testid="turnstile" />;
  },
}));

import ModularLoginForm, { formatLoginError } from '../ModularLoginForm';

const authSession = {
  access_token: 'test-token',
  user: {
    id: 'u1',
    email: 'test@test.com',
    role: 'authenticated',
    user_metadata: { name: 'Test User' },
    created_at: '2026-07-17T00:00:00Z',
  },
};

describe('ModularLoginForm', () => {
  const onSuccess = vi.fn();
  const onError = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    turnstileState.enabled = false;
    turnstileState.token = '';
    featureFlagsState.googleAuth = false;
    mockSignIn.mockResolvedValue({ session: authSession, error: null });
    mockSignUp.mockResolvedValue({ session: authSession, error: null });
    mockSignInWithOAuth.mockResolvedValue({ data: { url: 'https://accounts.google.com/o/oauth2/v2/auth?state=test' }, error: null });
  });

  it('submits login credentials and stores the auth snapshot', async () => {
    render(<ModularLoginForm onSuccess={onSuccess} onError={onError} />);

    fireEvent.click(screen.getByRole('button', { name: 'Submit' }));

    await waitFor(() => expect(mockSignIn).toHaveBeenCalledTimes(1));
    expect(mockSignIn).toHaveBeenCalledWith('test@test.com', 'pass', undefined);
    expect(onSuccess).toHaveBeenCalledTimes(1);
  });

  it('blocks submit until turnstile is solved', async () => {
    turnstileState.enabled = true;

    render(<ModularLoginForm onSuccess={onSuccess} onError={onError} />);

    fireEvent.click(screen.getByRole('button', { name: 'Submit' }));

    expect(onError).toHaveBeenCalledWith('Please complete the security verification');
    expect(mockSignIn).not.toHaveBeenCalled();
    expect(mockSignUp).not.toHaveBeenCalled();
  });

  it('submits register flow and surfaces confirmation when the session is pending', async () => {
    turnstileState.enabled = true;
    turnstileState.token = 'turnstile-token';
    mockSignUp.mockResolvedValueOnce({ session: null, error: null });

    render(
      <ModularLoginForm initialMode="register" onSuccess={onSuccess} onError={onError} />
    );

    await waitFor(() => expect(screen.getByTestId('turnstile')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Submit' }));

    await waitFor(() => expect(mockSignUp).toHaveBeenCalledTimes(1));
    expect(mockSignUp).toHaveBeenCalledWith('test@test.com', 'pass', 'turnstile-token');
    expect(onError).toHaveBeenCalledWith(
      'Check your email to confirm your account before signing in.'
    );
  });

  it('starts Google sign-in when the provider is enabled', async () => {
    featureFlagsState.googleAuth = true;

    render(<ModularLoginForm onSuccess={onSuccess} onError={onError} />);

    fireEvent.click(screen.getByRole('button', { name: 'Google login' }));

    await waitFor(() => expect(mockSignInWithOAuth).toHaveBeenCalledTimes(1));
    expect(mockSignInWithOAuth).toHaveBeenCalledWith(
      'google',
      'http://localhost:3000/google-callback'
    );
  });

  it('preserves non-Error login failures through the shared formatter', () => {
    expect(formatLoginError('oauth backend unavailable', 'Authentication failed')).toBe(
      'oauth backend unavailable'
    );
  });
});
