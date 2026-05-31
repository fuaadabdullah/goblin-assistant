import {
  bootstrapAuthSession,
  clearAuthSessionState,
  clearValidationCache,
} from '../auth-state';

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------

jest.mock('../api', () => ({
  apiClient: {
    validateToken: jest.fn(),
    logout: jest.fn(),
  },
}));

jest.mock('../../utils/auth-session', () => ({
  clearAuthSession: jest.fn(),
  getAuthToken: jest.fn(),
  isAuthenticated: jest.fn(),
  persistAuthSession: jest.fn(),
}));

import { apiClient } from '../api';
import {
  clearAuthSession,
  getAuthToken,
  isAuthenticated as checkAuth,
  persistAuthSession,
} from '../../utils/auth-session';

const mockValidateToken = apiClient.validateToken as jest.MockedFunction<
  typeof apiClient.validateToken
>;
const mockLogout = apiClient.logout as jest.MockedFunction<typeof apiClient.logout>;
const mockGetAuthToken = getAuthToken as jest.MockedFunction<typeof getAuthToken>;
const mockCheckAuth = checkAuth as jest.MockedFunction<typeof checkAuth>;
const mockClearAuthSession = clearAuthSession as jest.MockedFunction<typeof clearAuthSession>;
const mockPersistAuthSession = persistAuthSession as jest.MockedFunction<typeof persistAuthSession>;

const testUser = { id: 'u1', email: 'test@example.com', name: 'Test User', role: 'user' };

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function setLocalStorage(key: string, value: string) {
  window.localStorage.setItem(key, value);
}

function clearAll() {
  window.localStorage.clear();
  document.cookie.split(';').forEach((c) => {
    const name = c.trim().split('=')[0];
    if (name) document.cookie = `${name}=; Path=/; Max-Age=0`;
  });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  clearAll();
  clearValidationCache();
  jest.clearAllMocks();

  // Sensible defaults
  mockGetAuthToken.mockReturnValue(null);
  mockCheckAuth.mockReturnValue(false);
  mockLogout.mockResolvedValue(undefined);
});

describe('bootstrapAuthSession — SSR guard', () => {
  it('returns unauthenticated when window is undefined', async () => {
    const originalWindow = global.window;
    // @ts-expect-error — deliberate SSR simulation
    delete global.window;
    const snapshot = await bootstrapAuthSession();
    global.window = originalWindow;

    expect(snapshot.isAuthenticated).toBe(false);
    expect(snapshot.isHydrated).toBe(true);
  });
});

describe('bootstrapAuthSession — HttpOnly cookie path', () => {
  it('returns authenticated when goblin_auth cookie is set and no localStorage token', async () => {
    mockGetAuthToken.mockReturnValue(null);
    mockCheckAuth.mockReturnValue(true);

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.isAuthenticated).toBe(true);
    expect(snapshot.token).toBeNull();
    expect(snapshot.isHydrated).toBe(true);
    expect(mockValidateToken).not.toHaveBeenCalled();
  });

  it('includes cached user_data when present', async () => {
    mockGetAuthToken.mockReturnValue(null);
    mockCheckAuth.mockReturnValue(true);
    setLocalStorage('user_data', JSON.stringify(testUser));

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.isAuthenticated).toBe(true);
    expect(snapshot.user).toMatchObject({ id: 'u1' });
  });

  it('returns authenticated with null user when no user_data is cached', async () => {
    mockGetAuthToken.mockReturnValue(null);
    mockCheckAuth.mockReturnValue(true);

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.isAuthenticated).toBe(true);
    expect(snapshot.user).toBeNull();
  });

  it('migrates legacy auth_token out of localStorage when goblin_auth cookie is set', async () => {
    setLocalStorage('auth_token', 'old-legacy-token');
    mockCheckAuth.mockReturnValue(true);
    // After migration, getAuthToken returns null (cookie only)
    mockGetAuthToken.mockReturnValue(null);

    await bootstrapAuthSession();

    expect(window.localStorage.getItem('auth_token')).toBeNull();
  });
});

describe('bootstrapAuthSession — no session', () => {
  it('returns unauthenticated when no token and no auth cookie', async () => {
    mockGetAuthToken.mockReturnValue(null);
    mockCheckAuth.mockReturnValue(false);

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.isAuthenticated).toBe(false);
    expect(snapshot.token).toBeNull();
    expect(mockValidateToken).not.toHaveBeenCalled();
  });
});

describe('bootstrapAuthSession — legacy localStorage token path', () => {
  it('validates token and returns authenticated on success', async () => {
    const token = 'legacy.jwt.token';
    mockGetAuthToken.mockReturnValue(token);
    mockCheckAuth.mockReturnValue(false);
    setLocalStorage('user_data', JSON.stringify(testUser));

    mockValidateToken.mockResolvedValue({
      valid: true,
      user: testUser,
      expires_in: 3600,
    } as any);

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.isAuthenticated).toBe(true);
    expect(snapshot.token).toBe(token);
    expect(snapshot.user).toMatchObject({ id: 'u1' });
    expect(mockValidateToken).toHaveBeenCalledWith(token);
    expect(mockPersistAuthSession).toHaveBeenCalled();
  });

  it('clears session and returns unauthenticated when token is invalid', async () => {
    mockGetAuthToken.mockReturnValue('expired.token');
    mockCheckAuth.mockReturnValue(false);

    mockValidateToken.mockResolvedValue({ valid: false } as any);

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.isAuthenticated).toBe(false);
    expect(mockClearAuthSession).toHaveBeenCalled();
  });

  it('uses cached validation result on second call (no extra network requests)', async () => {
    const token = 'cached.token';
    mockGetAuthToken.mockReturnValue(token);
    mockCheckAuth.mockReturnValue(false);

    mockValidateToken.mockResolvedValue({ valid: true, user: testUser } as any);

    await bootstrapAuthSession();
    await bootstrapAuthSession();

    // validateToken should only be called once
    expect(mockValidateToken).toHaveBeenCalledTimes(1);
  });

  it('clears session on 401 backend response', async () => {
    mockGetAuthToken.mockReturnValue('stale.token');
    mockCheckAuth.mockReturnValue(false);

    const err = Object.assign(new Error('Unauthorized'), { status: 401 });
    mockValidateToken.mockRejectedValue(err);

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.isAuthenticated).toBe(false);
    expect(mockClearAuthSession).toHaveBeenCalled();
  });

  it('clears session on 403 backend response', async () => {
    mockGetAuthToken.mockReturnValue('forbidden.token');
    mockCheckAuth.mockReturnValue(false);

    const err = Object.assign(new Error('Forbidden'), { status: 403 });
    mockValidateToken.mockRejectedValue(err);

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.isAuthenticated).toBe(false);
    expect(mockClearAuthSession).toHaveBeenCalled();
  });

  it('fails closed on generic network error (no 401/403)', async () => {
    mockGetAuthToken.mockReturnValue('some.token');
    mockCheckAuth.mockReturnValue(false);

    mockValidateToken.mockRejectedValue(new Error('Network error'));

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.isAuthenticated).toBe(false);
    expect(mockClearAuthSession).toHaveBeenCalled();
  });

  it('falls back to stored user when validate response has no user', async () => {
    const token = 'token.no.user';
    mockGetAuthToken.mockReturnValue(token);
    mockCheckAuth.mockReturnValue(false);
    setLocalStorage('user_data', JSON.stringify(testUser));

    mockValidateToken.mockResolvedValue({ valid: true } as any);

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.user).toMatchObject({ id: 'u1' });
  });
});

describe('clearAuthSessionState', () => {
  it('calls logout, clears validation cache, and clears local session', async () => {
    mockLogout.mockResolvedValue(undefined);

    // Pre-populate cache so we can verify it's cleared
    const token = 'cached.token';
    mockGetAuthToken.mockReturnValue(token);
    mockCheckAuth.mockReturnValue(false);
    mockValidateToken.mockResolvedValue({ valid: true, user: testUser } as any);
    await bootstrapAuthSession();
    expect(mockValidateToken).toHaveBeenCalledTimes(1);

    await clearAuthSessionState();

    expect(mockLogout).toHaveBeenCalled();
    expect(mockClearAuthSession).toHaveBeenCalled();

    // Cache cleared — next bootstrapAuthSession should call validateToken again
    jest.clearAllMocks();
    mockGetAuthToken.mockReturnValue(token);
    mockCheckAuth.mockReturnValue(false);
    mockLogout.mockResolvedValue(undefined);
    mockValidateToken.mockResolvedValue({ valid: true, user: testUser } as any);
    await bootstrapAuthSession();
    expect(mockValidateToken).toHaveBeenCalledTimes(1);
  });

  it('still clears local session even when backend logout fails', async () => {
    mockLogout.mockRejectedValue(new Error('Network error'));

    await clearAuthSessionState();

    expect(mockClearAuthSession).toHaveBeenCalled();
  });
});
