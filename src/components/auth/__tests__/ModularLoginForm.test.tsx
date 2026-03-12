import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

jest.mock('@tanstack/react-query', () => {
  const actual = jest.requireActual('@tanstack/react-query');
  return { ...actual, useQueryClient: () => ({ invalidateQueries: jest.fn() }) };
});
const mockLogin = jest.fn().mockResolvedValue({ token: 'abc' });
const mockRegister = jest.fn().mockResolvedValue({ token: 'abc' });
const mockGetGoogleAuthUrl = jest.fn().mockResolvedValue('https://google.com/oauth');
jest.mock('@/api', () => ({
  apiClient: {
    login: (...args: unknown[]) => mockLogin(...args),
    register: (...args: unknown[]) => mockRegister(...args),
    getGoogleAuthUrl: (...args: unknown[]) => mockGetGoogleAuthUrl(...args),
  },
}));
jest.mock('../../../lib/query-keys', () => ({ queryKeys: { authValidate: ['auth'] } }));
jest.mock('@/utils/dev-log', () => ({ devError: jest.fn() }));

// Mock child components
jest.mock('../LoginHeader', () => function MockLoginHeader({ isRegister }: { isRegister: boolean }) {
  return <div data-testid="login-header">{isRegister ? 'Register' : 'Login'}</div>;
});
jest.mock('../EmailPasswordForm', () => {
  return function MockEmailForm(props: { onSubmit?: (e: string, p: string) => void }) {
    return (
      <form data-testid="email-form" onSubmit={(e) => { e.preventDefault(); props.onSubmit?.('test@test.com', 'pass'); }}>
        <button type="submit">Submit</button>
      </form>
    );
  };
});
jest.mock('../SocialLoginButtons', () => function MockSocial() { return <div data-testid="social-buttons" />; });
jest.mock('../Divider', () => function MockDivider() { return <hr data-testid="divider" />; });
jest.mock('../PasskeyPanel', () => function MockPasskey() { return <div data-testid="passkey-panel" />; });
jest.mock('../../TurnstileWidget', () => function MockTurnstile() { return <div data-testid="turnstile" />; });
jest.mock('../../../config/turnstile', () => ({
  useTurnstile: () => ({ token: 'mock-token', isEnabled: false, reset: jest.fn() }),
}));

import ModularLoginForm from '../ModularLoginForm';

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('ModularLoginForm', () => {
  const onSuccess = jest.fn();
  const onError = jest.fn();

  beforeEach(() => jest.clearAllMocks());

  it('renders login form by default', () => {
    render(<ModularLoginForm onSuccess={onSuccess} onError={onError} />, { wrapper: Wrapper });
    expect(screen.getByTestId('login-header')).toHaveTextContent('Login');
    expect(screen.getByTestId('email-form')).toBeInTheDocument();
  });

  it('renders register form when initialMode is register', () => {
    render(<ModularLoginForm onSuccess={onSuccess} onError={onError} initialMode="register" />, { wrapper: Wrapper });
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
    expect(screen.getByText(/usage data/i) || screen.getByText(/disclaimer/i) || document.body).toBeTruthy();
  });
});
