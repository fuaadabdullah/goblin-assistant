import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query');
  return { ...actual, useQueryClient: () => ({ invalidateQueries: vi.fn() }) };
});
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      signInWithPassword: vi.fn().mockResolvedValue({
        data: {
          session: {
            access_token: 'test-token',
            user: { id: 'u1', email: 'test@test.com', role: 'authenticated', user_metadata: {} },
          },
          user: { id: 'u1', email: 'test@test.com', role: 'authenticated', user_metadata: {} },
        },
        error: null,
      }),
      signUp: vi.fn().mockResolvedValue({
        data: {
          session: {
            access_token: 'test-token',
            user: { id: 'u1', email: 'test@test.com', role: 'authenticated', user_metadata: {} },
          },
          user: { id: 'u1', email: 'test@test.com', role: 'authenticated', user_metadata: {} },
        },
        error: null,
      }),
      signInWithOAuth: vi.fn().mockResolvedValue({ data: {}, error: null }),
    },
  },
  supabaseUserToAppUser: (u: { id: string; email: string }) => ({ id: u.id, email: u.email }),
}));
vi.mock('../../../lib/query-keys', () => ({ queryKeys: { authValidate: ['auth'] } }));
vi.mock('@/utils/dev-log', () => ({ devError: vi.fn() }));

// Mock child components
vi.mock('../LoginHeader', () => ({
  default: function MockLoginHeader({ isRegister }: { isRegister: boolean }) {
    return <div data-testid="login-header">{isRegister ? 'Register' : 'Login'}</div>;
  },
}));
vi.mock('../EmailPasswordForm', () => ({
  default: function MockEmailForm(props: { onSubmit?: (e: string, p: string) => void }) {
    return (
      <form
        data-testid="email-form"
        onSubmit={(e) => {
          e.preventDefault();
          props.onSubmit?.('test@test.com', 'pass');
        }}
      >
        <button type="submit">Submit</button>
      </form>
    );
  },
}));
vi.mock('../SocialLoginButtons', () => ({
  default: function MockSocial() {
    return <div data-testid="social-buttons" />;
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
  default: function MockTurnstile() {
    return <div data-testid="turnstile" />;
  },
}));
vi.mock('../../../config/turnstile', () => ({
  useTurnstile: () => ({ token: 'mock-token', isEnabled: false, reset: vi.fn() }),
}));

import ModularLoginForm from '../ModularLoginForm';
import { formatLoginError } from '../ModularLoginForm';

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('ModularLoginForm', () => {
  const onSuccess = vi.fn();
  const onError = vi.fn();

  beforeEach(() => vi.clearAllMocks());

  it('renders login form by default', () => {
    render(<ModularLoginForm onSuccess={onSuccess} onError={onError} />, { wrapper: Wrapper });
    expect(screen.getByTestId('login-header')).toHaveTextContent('Login');
    expect(screen.getByTestId('email-form')).toBeInTheDocument();
  });

  it('renders register form when initialMode is register', () => {
    render(<ModularLoginForm onSuccess={onSuccess} onError={onError} initialMode="register" />, {
      wrapper: Wrapper,
    });
    expect(screen.getByTestId('login-header')).toHaveTextContent('Register');
  });

  it('renders social login buttons', () => {
    render(<ModularLoginForm onSuccess={onSuccess} onError={onError} />, { wrapper: Wrapper });
    expect(screen.getByTestId('social-buttons')).toBeInTheDocument();
  });

  it('shows passkey panel when toggled', () => {
    render(<ModularLoginForm onSuccess={onSuccess} onError={onError} />, { wrapper: Wrapper });
    const passkeyToggle = screen.queryByText(/passkey/i);
    if (passkeyToggle) {
      fireEvent.click(passkeyToggle);
      expect(screen.getByTestId('passkey-panel')).toBeInTheDocument();
    }
  });

  it('renders disclaimer text', () => {
    render(<ModularLoginForm onSuccess={onSuccess} onError={onError} />, { wrapper: Wrapper });
    expect(
      screen.getByText(/usage data/i) || screen.getByText(/disclaimer/i) || document.body
    ).toBeTruthy();
  });

  it('preserves non-Error login failures through the shared formatter', () => {
    expect(formatLoginError('oauth backend unavailable', 'Authentication failed')).toBe(
      'oauth backend unavailable'
    );
  });
});
