import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import PasskeyPanel from '../PasskeyPanel';

const {
  mockSetQueryData,
  mockPasskeyChallenge,
  mockPasskeyRegister,
  mockPasskeyAuth,
  mockPersistAuthSession,
  mockCreate,
  mockGet,
} = vi.hoisted(() => ({
  mockSetQueryData: vi.fn(),
  mockPasskeyChallenge: vi.fn(),
  mockPasskeyRegister: vi.fn(),
  mockPasskeyAuth: vi.fn(),
  mockPersistAuthSession: vi.fn(),
  mockCreate: vi.fn(),
  mockGet: vi.fn(),
}));

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ setQueryData: mockSetQueryData }),
}));

vi.mock('@/lib/api', () => ({
  apiClient: {
    passkeyChallenge: (...args: unknown[]) => mockPasskeyChallenge(...args),
    passkeyRegister: (...args: unknown[]) => mockPasskeyRegister(...args),
    passkeyAuth: (...args: unknown[]) => mockPasskeyAuth(...args),
  },
}));

vi.mock('@/utils/auth-session', () => ({
  persistAuthSession: mockPersistAuthSession,
}));

vi.mock('@/lib/query-keys', () => ({
  queryKeys: { authValidate: ['auth', 'validate'] },
}));

vi.mock('@/lib/error/toast', () => ({
  getUserMessage: (error: unknown) => (error instanceof Error ? error.message : String(error)),
}));

type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    email: string;
    role: string;
    name?: string;
  };
};

const asBuffer = (value: string) => new TextEncoder().encode(value).buffer;

const setWebAuthnSupport = (supported: boolean) => {
  if (supported) {
    Object.defineProperty(window, 'PublicKeyCredential', {
      value: class {},
      writable: true,
      configurable: true,
    });
    return;
  }

  Reflect.deleteProperty(window, 'PublicKeyCredential');
};

const setNavigatorCredentials = () => {
  Object.defineProperty(navigator, 'credentials', {
    value: { create: mockCreate, get: mockGet },
    writable: true,
    configurable: true,
  });
};

const makeRegisterChallenge = (
  overrides: Partial<{
    challenge: string;
    rp: { name: string; id: string };
    user: { id: string; name: string; displayName: string };
    pubKeyCredParams: Array<{ type: string; alg: number }>;
  }> = {}
) => ({
  publicKey: {
    challenge: 'dGVzdA',
    rp: { name: 'Goblin', id: 'localhost' },
    user: { id: 'dXNlcg', name: 'test@example.com', displayName: 'Test User' },
    pubKeyCredParams: [{ type: 'public-key', alg: -7 }],
    ...overrides,
  },
});

const makeAuthChallenge = (
  overrides: Partial<{
    challenge: string;
    rpId?: string;
    allowCredentials?: Array<{ type: string; id: string }>;
    timeout?: number;
    userVerification?: string;
  }> = {}
) => ({
  publicKey: {
    challenge: 'YXV0aA',
    rpId: 'localhost',
    allowCredentials: [{ type: 'public-key', id: 'Y3JlZA' }],
    ...overrides,
  },
});

const makeCredential = (
  options: { includeRawId?: boolean; includeResponse?: boolean } = {}
) => {
  const credential: Record<string, unknown> = {
    id: 'credential-id',
    type: 'public-key',
  };

  if (options.includeRawId !== false) {
    credential.rawId = asBuffer('raw-id');
  }

  if (options.includeResponse !== false) {
    credential.response = {
      attestationObject: asBuffer('attestation'),
      clientDataJSON: asBuffer('client-data'),
      authenticatorData: asBuffer('authenticator-data'),
      signature: asBuffer('signature'),
      userHandle: asBuffer('user-handle'),
    };
  }

  return credential as PublicKeyCredential;
};

const makeAuthResponse = (accessToken = 'auth-token'): AuthResponse => ({
  access_token: accessToken,
  refresh_token: 'refresh-token',
  token_type: 'bearer',
  expires_in: 3600,
  user: {
    id: 'u1',
    email: 'test@example.com',
    role: 'authenticated',
    name: 'Test User',
  },
});

describe('PasskeyPanel', () => {
  const onSuccess = vi.fn();
  const onError = vi.fn();

  const renderPanel = (
    props: Partial<{
      email: string;
      onSuccess: () => void;
      onError: (message: string) => void;
    }> = {}
  ) =>
    render(
      <PasskeyPanel
        email="test@example.com"
        onSuccess={onSuccess}
        onError={onError}
        {...props}
      />
    );

  beforeEach(() => {
    vi.clearAllMocks();
    setWebAuthnSupport(true);
    setNavigatorCredentials();
    mockPasskeyChallenge.mockReset();
    mockPasskeyRegister.mockReset();
    mockPasskeyAuth.mockReset();
    mockSetQueryData.mockReset();
    mockPersistAuthSession.mockReset();
    mockCreate.mockReset();
    mockGet.mockReset();
    mockPasskeyRegister.mockResolvedValue(undefined);
    mockPasskeyAuth.mockResolvedValue(makeAuthResponse());
    mockCreate.mockResolvedValue(makeCredential({ includeRawId: false, includeResponse: false }));
    mockGet.mockResolvedValue(makeCredential({ includeRawId: false, includeResponse: false }));
  });

  it('blocks submit when email is missing', () => {
    renderPanel({ email: '' });

    fireEvent.click(screen.getByRole('button', { name: /register passkey/i }));

    expect(onError).toHaveBeenCalledWith('Enter email above before using passkey');
    expect(mockPasskeyChallenge).not.toHaveBeenCalled();
  });

  it('reports unsupported WebAuthn in the register flow', () => {
    setWebAuthnSupport(false);
    renderPanel();

    fireEvent.click(screen.getByRole('button', { name: /register passkey/i }));

    expect(onError).toHaveBeenCalledWith('WebAuthn not supported in this browser');
    expect(mockPasskeyChallenge).not.toHaveBeenCalled();
  });

  it('reports unsupported WebAuthn in the authentication flow', () => {
    setWebAuthnSupport(false);
    renderPanel();

    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));

    expect(onError).toHaveBeenCalledWith('WebAuthn not supported in this browser');
    expect(mockPasskeyChallenge).not.toHaveBeenCalled();
  });

  it('rejects a verification challenge in the register flow', async () => {
    mockPasskeyChallenge.mockResolvedValueOnce(makeAuthChallenge());

    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /register passkey/i }));

    await waitFor(() => expect(mockPasskeyChallenge).toHaveBeenCalledTimes(1));
    expect(onError).toHaveBeenCalledWith('Invalid passkey registration challenge');
    expect(mockCreate).not.toHaveBeenCalled();
    expect(mockPasskeyRegister).not.toHaveBeenCalled();
  });

  it('registers a passkey with a minimal challenge payload', async () => {
    mockPasskeyChallenge.mockResolvedValueOnce(
      makeRegisterChallenge({
        challenge: '',
        user: { id: '', name: 'test@example.com', displayName: 'Test User' },
      })
    );

    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /register passkey/i }));

    await waitFor(() => expect(mockPasskeyRegister).toHaveBeenCalledTimes(1));
    expect(mockCreate).toHaveBeenCalledTimes(1);

    const createOptions = mockCreate.mock.calls[0][0] as {
      publicKey: { challenge: string; user: { id: string } };
    };
    expect(createOptions.publicKey.challenge).toBe('');
    expect(createOptions.publicKey.user.id).toBe('');
    expect(mockPasskeyRegister).toHaveBeenCalledWith(
      'test@example.com',
      expect.objectContaining({
        id: 'credential-id',
        type: 'public-key',
      })
    );
    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
  });

  it('registers a passkey with a full challenge payload', async () => {
    mockPasskeyChallenge.mockResolvedValueOnce(makeRegisterChallenge());
    mockCreate.mockResolvedValueOnce(makeCredential());
    mockPasskeyRegister.mockResolvedValueOnce(undefined);

    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /register passkey/i }));

    await waitFor(() => expect(mockPasskeyRegister).toHaveBeenCalledTimes(1));

    const createOptions = mockCreate.mock.calls[0][0] as {
      publicKey: { challenge: Uint8Array; user: { id: Uint8Array } };
    };
    expect(createOptions.publicKey.challenge).toBeInstanceOf(Uint8Array);
    expect(createOptions.publicKey.user.id).toBeInstanceOf(Uint8Array);
    expect(mockPasskeyRegister).toHaveBeenCalledWith(
      'test@example.com',
      expect.objectContaining({
        id: 'credential-id',
        type: 'public-key',
        rawId: expect.any(String),
        response: expect.objectContaining({
          attestationObject: expect.any(String),
          clientDataJSON: expect.any(String),
          authenticatorData: expect.any(String),
          signature: expect.any(String),
          userHandle: expect.any(String),
        }),
      })
    );
    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
  });

  it('rejects a null registration credential', async () => {
    mockPasskeyChallenge.mockResolvedValueOnce(makeRegisterChallenge());
    mockCreate.mockResolvedValueOnce(null);

    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /register passkey/i }));

    await waitFor(() => expect(mockPasskeyChallenge).toHaveBeenCalledTimes(1));
    expect(onError).toHaveBeenCalledWith('Failed to encode passkey credential');
    expect(mockPasskeyRegister).not.toHaveBeenCalled();
  });

  it('rejects a verification challenge in the authentication flow', async () => {
    mockPasskeyChallenge.mockResolvedValueOnce(makeRegisterChallenge());

    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));

    await waitFor(() => expect(mockPasskeyChallenge).toHaveBeenCalledTimes(1));
    expect(onError).toHaveBeenCalledWith('Invalid passkey verification challenge');
    expect(mockGet).not.toHaveBeenCalled();
    expect(mockPasskeyAuth).not.toHaveBeenCalled();
  });

  it('authenticates with a minimal challenge payload', async () => {
    mockPasskeyChallenge.mockResolvedValueOnce(
      makeAuthChallenge({
        challenge: '',
        allowCredentials: undefined,
      })
    );

    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));

    await waitFor(() => expect(mockPasskeyAuth).toHaveBeenCalledTimes(1));

    const getOptions = mockGet.mock.calls[0][0] as {
      publicKey: { challenge: string; allowCredentials?: Array<{ id: string }> };
    };
    expect(getOptions.publicKey.challenge).toBe('');
    expect(getOptions.publicKey.allowCredentials).toBeUndefined();
    expect(mockPasskeyAuth).toHaveBeenCalledWith(
      'test@example.com',
      expect.objectContaining({
        id: 'credential-id',
        type: 'public-key',
      })
    );
    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
  });

  it('authenticates with a full challenge payload', async () => {
    mockPasskeyChallenge.mockResolvedValueOnce(makeAuthChallenge());
    mockGet.mockResolvedValueOnce(makeCredential());
    mockPasskeyAuth.mockResolvedValueOnce(makeAuthResponse());

    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));

    await waitFor(() => expect(mockPasskeyAuth).toHaveBeenCalledTimes(1));

    const getOptions = mockGet.mock.calls[0][0] as {
      publicKey: { challenge: Uint8Array; allowCredentials?: Array<{ id: Uint8Array }> };
    };
    expect(getOptions.publicKey.challenge).toBeInstanceOf(Uint8Array);
    expect(getOptions.publicKey.allowCredentials?.[0]?.id).toBeInstanceOf(Uint8Array);
    expect(mockPersistAuthSession).toHaveBeenCalledWith({
      token: 'auth-token',
      refreshToken: 'refresh-token',
      user: expect.objectContaining({
        id: 'u1',
        email: 'test@example.com',
      }),
      expiresIn: 3600,
    });
    expect(mockSetQueryData).toHaveBeenCalledWith(['auth', 'validate'], {
      token: 'auth-token',
      user: expect.objectContaining({
        id: 'u1',
        email: 'test@example.com',
      }),
      isAuthenticated: true,
      isHydrated: true,
    });
    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/passkey authentication successful/i)).toBeInTheDocument();
  });

  it('rejects a null authentication assertion', async () => {
    mockPasskeyChallenge.mockResolvedValueOnce(makeAuthChallenge());
    mockGet.mockResolvedValueOnce(null);

    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));

    await waitFor(() => expect(mockPasskeyChallenge).toHaveBeenCalledTimes(1));
    expect(onError).toHaveBeenCalledWith('Failed to encode passkey assertion');
    expect(mockPasskeyAuth).not.toHaveBeenCalled();
  });

  it('rejects an auth response without an access token', async () => {
    mockPasskeyChallenge.mockResolvedValueOnce(makeAuthChallenge());
    mockGet.mockResolvedValueOnce(makeCredential());
    mockPasskeyAuth.mockResolvedValueOnce(makeAuthResponse(''));

    renderPanel();
    fireEvent.click(screen.getByRole('button', { name: /authenticate/i }));

    await waitFor(() => expect(mockPasskeyAuth).toHaveBeenCalledTimes(1));
    expect(onError).toHaveBeenCalledWith('Authentication failed - invalid server response');
    expect(mockPersistAuthSession).not.toHaveBeenCalled();
    expect(mockSetQueryData).not.toHaveBeenCalled();
  });
});
