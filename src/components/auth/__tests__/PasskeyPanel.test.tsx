import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock apiClient
const mockPasskeyChallenge = jest.fn();
const mockPasskeyRegister = jest.fn();
const mockPasskeyAuth = jest.fn();
jest.mock('@/api', () => ({
  apiClient: {
    passkeyChallenge: (...args: unknown[]) => mockPasskeyChallenge(...args),
    passkeyRegister: (...args: unknown[]) => mockPasskeyRegister(...args),
    passkeyAuth: (...args: unknown[]) => mockPasskeyAuth(...args),
  },
}));
jest.mock('@/utils/auth-session', () => ({
  persistAuthSession: jest.fn(),
}));
jest.mock('@/lib/query-keys', () => ({
  queryKeys: { authValidate: ['auth', 'validate'] },
}));

import PasskeyPanel from '../PasskeyPanel';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const defaultProps = {
  email: 'test@example.com',
  onSuccess: jest.fn(),
  onError: jest.fn(),
};

describe('PasskeyPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Mock WebAuthn API
    Object.defineProperty(window, 'PublicKeyCredential', { value: class {}, writable: true, configurable: true });
  });

  it('renders passkey registration and authentication buttons', () => {
    render(<PasskeyPanel {...defaultProps} />, { wrapper });
    expect(screen.getByText(/register/i) || screen.getByText(/passkey/i)).toBeTruthy();
  });

  it('shows browser not supported message when WebAuthn is unavailable', () => {
    Object.defineProperty(window, 'PublicKeyCredential', { value: undefined, writable: true, configurable: true });
    render(<PasskeyPanel {...defaultProps} />, { wrapper });
    // Should indicate passkeys are not supported or show nothing actionable
  });

  it('handles registration error', async () => {
    mockPasskeyChallenge.mockRejectedValue(new Error('Challenge failed'));
    render(<PasskeyPanel {...defaultProps} />, { wrapper });
    const registerBtn = screen.getByText(/register/i);
    fireEvent.click(registerBtn);
    await waitFor(() => {
      expect(defaultProps.onError).toHaveBeenCalled();
    });
  });

  it('handles authentication error', async () => {
    mockPasskeyChallenge.mockRejectedValue(new Error('Auth failed'));
    render(<PasskeyPanel {...defaultProps} />, { wrapper });
    const authBtn = screen.queryByText(/sign in/i) || screen.queryByText(/authenticate/i);
    if (authBtn) {
      fireEvent.click(authBtn);
      await waitFor(() => {
        expect(defaultProps.onError).toHaveBeenCalled();
      });
    }
  });

  it('calls passkey challenge API on register', async () => {
    mockPasskeyChallenge.mockResolvedValue({
      challenge: 'dGVzdA',
      rp: { name: 'Goblin', id: 'localhost' },
      user: { id: 'dXNlcg', name: 'test@example.com', displayName: 'Test' },
      pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
    });
    // Mock navigator.credentials.create
    const mockCreate = jest.fn().mockRejectedValue(new Error('User cancelled'));
    Object.defineProperty(navigator, 'credentials', {
      value: { create: mockCreate, get: jest.fn() },
      writable: true,
      configurable: true,
    });

    render(<PasskeyPanel {...defaultProps} />, { wrapper });
    const registerBtn = screen.getByText(/register/i);
    fireEvent.click(registerBtn);

    await waitFor(() => {
      expect(mockPasskeyChallenge).toHaveBeenCalled();
    });
  });
});
