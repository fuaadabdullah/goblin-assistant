import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import PasskeyPanel from '../PasskeyPanel';

const {
  mockSetQueryData,
  mockPasskeyChallenge,
  mockPasskeyRegister,
  mockPasskeyAuth,
  mockBrowserSupportsWebAuthn,
  mockStartRegistration,
  mockStartAuthentication,
  mockVerifyOtp,
  mockSnapshotFromSupabaseSession,
} = vi.hoisted(() => ({
  mockSetQueryData: vi.fn(),
  mockPasskeyChallenge: vi.fn(),
  mockPasskeyRegister: vi.fn(),
  mockPasskeyAuth: vi.fn(),
  mockBrowserSupportsWebAuthn: vi.fn(),
  mockStartRegistration: vi.fn(),
  mockStartAuthentication: vi.fn(),
  mockVerifyOtp: vi.fn(),
  mockSnapshotFromSupabaseSession: vi.fn(),
}));

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ setQueryData: mockSetQueryData }),
}));

vi.mock('@simplewebauthn/browser', () => ({
  browserSupportsWebAuthn: () => mockBrowserSupportsWebAuthn(),
  startRegistration: (...args: unknown[]) => mockStartRegistration(...args),
  startAuthentication: (...args: unknown[]) => mockStartAuthentication(...args),
}));

vi.mock('@/lib/api', () => ({
  apiClient: {
    passkeyChallenge: (...args: unknown[]) => mockPasskeyChallenge(...args),
    passkeyRegister: (...args: unknown[]) => mockPasskeyRegister(...args),
    passkeyAuth: (...args: unknown[]) => mockPasskeyAuth(...args),
  },
}));

vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      verifyOtp: (...args: unknown[]) => mockVerifyOtp(...args),
    },
  },
}));

vi.mock('@/lib/auth-state', () => ({
  snapshotFromSupabaseSession: (session: unknown) => mockSnapshotFromSupabaseSession(session),
}));

vi.mock('@/lib/query-keys', () => ({
  queryKeys: { authValidate: ['auth', 'validate'] },
}));

vi.mock('@/lib/error/toast', () => ({
  getUserMessage: (error: unknown) => (error instanceof Error ? error.message : String(error)),
}));

const registrationOptions = {
  publicKey: {
    challenge: 'dGVzdA',
    rp: { name: 'Goblin', id: 'localhost' },
    user: { id: 'dXNlcg', name: 'test@example.com', displayName: 'Test User' },
    pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
  },
};

const authenticationOptions = {
  publicKey: {
    challenge: 'YXV0aA',
    rpId: 'localhost',
    allowCredentials: [{ type: 'public-key', id: 'Y3JlZA' }],
  },
};

describe('PasskeyPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBrowserSupportsWebAuthn.mockReturnValue(true);
    mockSnapshotFromSupabaseSession.mockReturnValue({
      token: 'supabase-token',
      user: { id: 'u1', email: 'test@example.com' },
      isAuthenticated: true,
      isHydrated: true,
    });
  });

  const renderPanel = (onSuccess = vi.fn(), onError = vi.fn()) =>
    render(<PasskeyPanel email="test@example.com" onSuccess={onSuccess} onError={onError} />);

  it('requires an email before using passkey', async () => {
    const onError = vi.fn();
    render(<PasskeyPanel email="" onSuccess={vi.fn()} onError={onError} />);
    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));
    expect(onError).toHaveBeenCalledWith('Enter email above before using passkey');
    expect(mockPasskeyChallenge).not.toHaveBeenCalled();
  });

  it('errors when WebAuthn is unsupported', async () => {
    mockBrowserSupportsWebAuthn.mockReturnValue(false);
    const onError = vi.fn();
    renderPanel(vi.fn(), onError);
    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));
    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith('WebAuthn not supported in this browser')
    );
  });

  it('registers a passkey via @simplewebauthn/browser', async () => {
    const onSuccess = vi.fn();
    mockPasskeyChallenge.mockResolvedValueOnce(registrationOptions);
    mockStartRegistration.mockResolvedValueOnce({ id: 'cred', type: 'public-key' });
    mockPasskeyRegister.mockResolvedValueOnce({ message: 'ok' });

    renderPanel(onSuccess);
    fireEvent.click(screen.getByRole('button', { name: /register passkey/i }));

    await waitFor(() => expect(mockPasskeyRegister).toHaveBeenCalledTimes(1));
    expect(mockStartRegistration).toHaveBeenCalledWith({
      optionsJSON: registrationOptions.publicKey,
    });
    expect(onSuccess).toHaveBeenCalledTimes(1);
  });

  it('rejects registration when the account already has a passkey', async () => {
    const onError = vi.fn();
    mockPasskeyChallenge.mockResolvedValueOnce(authenticationOptions);

    renderPanel(vi.fn(), onError);
    fireEvent.click(screen.getByRole('button', { name: /register passkey/i }));

    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith('This account already has a passkey registered')
    );
    expect(mockStartRegistration).not.toHaveBeenCalled();
  });

  it('authenticates and establishes a Supabase session', async () => {
    const onSuccess = vi.fn();
    mockPasskeyChallenge.mockResolvedValueOnce(authenticationOptions);
    mockStartAuthentication.mockResolvedValueOnce({ id: 'cred', type: 'public-key' });
    mockPasskeyAuth.mockResolvedValueOnce({ token_hash: 'hashed', user: { id: 'u1' } });
    mockVerifyOtp.mockResolvedValueOnce({
      data: { session: { access_token: 'supabase-token', user: { id: 'u1' } } },
      error: null,
    });

    renderPanel(onSuccess);
    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));

    await waitFor(() => expect(mockVerifyOtp).toHaveBeenCalledTimes(1));
    expect(mockVerifyOtp).toHaveBeenCalledWith({ token_hash: 'hashed', type: 'magiclink' });
    expect(mockSetQueryData).toHaveBeenCalledWith(
      ['auth', 'validate'],
      expect.objectContaining({ isAuthenticated: true })
    );
    expect(onSuccess).toHaveBeenCalledTimes(1);
  });

  it('rejects authentication when no token hash is returned', async () => {
    const onError = vi.fn();
    mockPasskeyChallenge.mockResolvedValueOnce(authenticationOptions);
    mockStartAuthentication.mockResolvedValueOnce({ id: 'cred', type: 'public-key' });
    mockPasskeyAuth.mockResolvedValueOnce({ token_hash: '', user: null });

    renderPanel(vi.fn(), onError);
    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));

    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith('Authentication failed - invalid server response')
    );
    expect(mockVerifyOtp).not.toHaveBeenCalled();
  });

  it('rejects authentication when verifyOtp fails', async () => {
    const onError = vi.fn();
    mockPasskeyChallenge.mockResolvedValueOnce(authenticationOptions);
    mockStartAuthentication.mockResolvedValueOnce({ id: 'cred', type: 'public-key' });
    mockPasskeyAuth.mockResolvedValueOnce({ token_hash: 'hashed', user: { id: 'u1' } });
    mockVerifyOtp.mockResolvedValueOnce({
      data: { session: null },
      error: new Error('otp failed'),
    });

    renderPanel(vi.fn(), onError);
    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));

    await waitFor(() => expect(onError).toHaveBeenCalledWith('otp failed'));
  });

  it('rejects authentication when no passkey is registered', async () => {
    const onError = vi.fn();
    mockPasskeyChallenge.mockResolvedValueOnce(registrationOptions);

    renderPanel(vi.fn(), onError);
    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));

    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith('No passkey registered for this account')
    );
    expect(mockStartAuthentication).not.toHaveBeenCalled();
  });
});
