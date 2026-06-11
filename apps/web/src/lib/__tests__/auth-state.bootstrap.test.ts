import { bootstrapAuthSession, clearAuthSessionState, clearValidationCache } from '../auth-state';

// ---------------------------------------------------------------------------
// Module mocks — factories run at hoist time, so no top-level var refs allowed
// ---------------------------------------------------------------------------

vi.mock('../supabase', () => ({
  authGetSession: vi.fn(),
  authSignOut: vi.fn(),
  supabaseUserToAppUser: (u: {
    id: string;
    email?: string;
    role?: string;
    user_metadata?: Record<string, unknown>;
    created_at?: string;
  }) => ({
    id: u.id,
    email: u.email ?? '',
    name: u.user_metadata?.name as string | undefined,
    role: u.role ?? 'authenticated',
    created_at: u.created_at,
  }),
}));

vi.mock('../../utils/auth-session', () => ({
  clearAuthSession: vi.fn(),
}));

// Get references to the mock functions after hoisting resolves
import { authGetSession, authSignOut } from '../supabase';
import { clearAuthSession } from '../../utils/auth-session';

const mockGetSession = authGetSession as vi.MockedFunction<typeof authGetSession>;
const mockSignOut = authSignOut as vi.MockedFunction<typeof authSignOut>;
const mockClearAuthSession = clearAuthSession as vi.MockedFunction<typeof clearAuthSession>;

const testUser = {
  id: 'u1',
  email: 'test@example.com',
  role: 'authenticated',
  user_metadata: { name: 'Test User' },
  created_at: '2024-01-01T00:00:00Z',
};

const testSession = {
  access_token: 'supabase.jwt.token',
  user: testUser,
};

beforeEach(() => {
  vi.clearAllMocks();
  clearValidationCache();
  mockSignOut.mockResolvedValue({ error: null });
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

describe('bootstrapAuthSession — Supabase session present', () => {
  it('returns authenticated with user when session exists', async () => {
    mockGetSession.mockResolvedValue({ session: testSession as any, error: null });

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.isAuthenticated).toBe(true);
    expect(snapshot.isHydrated).toBe(true);
    expect(snapshot.token).toBe(testSession.access_token);
    expect(snapshot.user).toMatchObject({ id: 'u1', email: 'test@example.com' });
    expect(mockGetSession).toHaveBeenCalledTimes(1);
  });

  it('maps user name from user_metadata', async () => {
    mockGetSession.mockResolvedValue({ session: testSession as any, error: null });

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.user?.name).toBe('Test User');
  });
});

describe('bootstrapAuthSession — no session', () => {
  it('returns unauthenticated when Supabase has no session', async () => {
    mockGetSession.mockResolvedValue({ session: null, error: null });

    const snapshot = await bootstrapAuthSession();

    expect(snapshot.isAuthenticated).toBe(false);
    expect(snapshot.token).toBeNull();
    expect(snapshot.user).toBeNull();
    expect(snapshot.isHydrated).toBe(true);
    expect(mockClearAuthSession).toHaveBeenCalled();
  });
});

describe('clearAuthSessionState', () => {
  it('calls supabase.auth.signOut and clears local session', async () => {
    await clearAuthSessionState();

    expect(mockSignOut).toHaveBeenCalled();
    expect(mockClearAuthSession).toHaveBeenCalled();
  });

  it('still clears local session even when signOut errors', async () => {
    mockSignOut.mockRejectedValue(new Error('Network error'));

    await clearAuthSessionState().catch(() => {});
    expect(mockClearAuthSession).toHaveBeenCalled();
  });
});
