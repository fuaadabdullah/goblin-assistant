import { render } from '@testing-library/react';
import AuthBootstrapper from '../AuthBootstrapper';
import * as supabaseModule from '../../lib/supabase';
import { clearAuthSession } from '../../utils/auth-session';
import * as reactQuery from '@tanstack/react-query';

vi.mock('../../lib/supabase');
vi.mock('../../utils/auth-session');
vi.mock('../../hooks/api/useAuthSession', () => ({
  useAuthSession: vi.fn(),
}));
vi.mock('@tanstack/react-query', () => ({
  useQueryClient: vi.fn(),
  useQuery: vi.fn(),
}));
vi.mock('../../lib/api/http-client', () => ({
  attachSupabaseInterceptor: vi.fn(() => Promise.resolve()),
}));

describe('AuthBootstrapper', () => {
  let mockCallback: ((event: string) => void) | null = null;
  let unsubscribeFn: (() => void) | null = null;

  beforeEach(() => {
    vi.clearAllMocks();
    mockCallback = null;
    unsubscribeFn = null;

    // Mock authOnStateChange to capture the callback
    vi.mocked(supabaseModule.authOnStateChange).mockImplementation((callback) => {
      mockCallback = callback;
      unsubscribeFn = vi.fn();
      return unsubscribeFn;
    });

    // Mock clearAuthSession
    vi.mocked(clearAuthSession).mockImplementation(() => {});

    // Mock useQueryClient
    const mockQueryClient = {
      invalidateQueries: vi.fn(),
    };
    vi.mocked(reactQuery.useQueryClient).mockReturnValue(mockQueryClient as any);
  });

  it('renders without crashing', () => {
    const { container } = render(<AuthBootstrapper />);
    expect(container).toBeInTheDocument();
  });

  it('subscribes to auth state changes', () => {
    render(<AuthBootstrapper />);
    expect(vi.mocked(supabaseModule.authOnStateChange)).toHaveBeenCalled();
  });

  it('clears auth session on SIGNED_OUT event', () => {
    render(<AuthBootstrapper />);

    if (mockCallback) {
      mockCallback('SIGNED_OUT');
    }

    expect(vi.mocked(clearAuthSession)).toHaveBeenCalled();
  });

  it('invalidates auth query on SIGNED_OUT event', () => {
    const { useQueryClient } = reactQuery;
    render(<AuthBootstrapper />);

    if (mockCallback) {
      mockCallback('SIGNED_OUT');
    }

    const mockQueryClient = vi.mocked(useQueryClient).mock.results[0]?.value;
    if (mockQueryClient) {
      expect(mockQueryClient.invalidateQueries).toHaveBeenCalledWith({
        queryKey: expect.arrayContaining(['auth', 'validate']),
      });
    }
  });

  it('invalidates auth query on non-SIGNED_OUT events', () => {
    const { useQueryClient } = reactQuery;
    render(<AuthBootstrapper />);

    if (mockCallback) {
      mockCallback('SIGNED_IN');
      mockCallback('TOKEN_REFRESHED');
    }

    const mockQueryClient = vi.mocked(useQueryClient).mock.results[0]?.value;
    if (mockQueryClient) {
      expect(mockQueryClient.invalidateQueries).toHaveBeenCalledTimes(2);
    }
  });

  it('does not clear auth session on SIGNED_IN event', () => {
    render(<AuthBootstrapper />);

    if (mockCallback) {
      mockCallback('SIGNED_IN');
    }

    expect(vi.mocked(clearAuthSession)).not.toHaveBeenCalled();
  });
});
