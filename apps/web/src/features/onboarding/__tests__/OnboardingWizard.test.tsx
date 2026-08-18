import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('next/link', () => ({
  default: function MockLink({
    children,
    href,
    className,
  }: {
    children: React.ReactNode;
    href: string;
    className?: string;
  }) {
    return (
      <a href={href} className={className}>
        {children}
      </a>
    );
  },
}));

const mockPush = vi.fn().mockResolvedValue(true);
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/onboarding',
}));
vi.mock('../../../components/Seo', () => ({
  default: function MockSeo() {
    return null;
  },
}));

const mockProviderSettings = vi.fn();
vi.mock('../../../hooks/api/useSettings', () => ({
  useProviderSettings: () => mockProviderSettings(),
}));

import OnboardingWizard from '../OnboardingWizard';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const createLocalStorage = (): Storage => {
  const entries = new Map<string, string>();
  return {
    clear: () => entries.clear(),
    getItem: (key: string) => entries.get(key) ?? null,
    key: (index: number) => Array.from(entries.keys())[index] ?? null,
    removeItem: (key: string) => {
      entries.delete(key);
    },
    setItem: (key: string, value: string) => {
      entries.set(key, value);
    },
    get length() {
      return entries.size;
    },
  } as Storage;
};

describe('OnboardingWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const localStorage = createLocalStorage();
    Object.defineProperty(globalThis, 'localStorage', {
      configurable: true,
      value: localStorage,
    });
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      value: localStorage,
    });
    mockProviderSettings.mockReturnValue({
      data: [
        { name: 'openai', enabled: true, models: ['gpt-4'] },
        { name: 'ollama', enabled: false, models: [] },
      ],
    });
  });

  it('renders provider setup summary', () => {
    render(<OnboardingWizard />, { wrapper });
    expect(screen.getByText('First-run setup')).toBeInTheDocument();
    expect(screen.getByText('1 provider ready for use.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open Settings' })).toHaveAttribute(
      'href',
      '/settings'
    );
  });

  it('shows provider settings loading state before the query resolves', () => {
    mockProviderSettings.mockReturnValueOnce({
      data: undefined,
      isLoading: true,
      isFetching: false,
    });

    render(<OnboardingWizard />, { wrapper });

    expect(screen.getByText('Checking provider configuration...')).toBeInTheDocument();
    expect(screen.getByText('Loading providers')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('navigates through wizard steps', () => {
    render(<OnboardingWizard />, { wrapper });
    fireEvent.click(screen.getByText('Next'));
    expect(screen.getByRole('link', { name: 'Start chat' })).toHaveAttribute(
      'href',
      expect.stringContaining('/chat?prompt=')
    );
    fireEvent.click(screen.getByText('Next'));
    expect(screen.getByRole('link', { name: 'Open Search' })).toHaveAttribute('href', '/search');
  });

  it('updates selected starter prompt link', () => {
    render(<OnboardingWizard />, { wrapper });
    fireEvent.click(screen.getByText('First chat'));
    fireEvent.click(
      screen.getByText('Compare provider options for a cost-sensitive coding workflow.')
    );
    expect(screen.getByRole('link', { name: 'Start chat' })).toHaveAttribute(
      'href',
      expect.stringContaining('Compare%20provider%20options')
    );
  });

  it('persists completion on complete', async () => {
    render(<OnboardingWizard />, { wrapper });
    fireEvent.click(screen.getByText('Search demo'));
    fireEvent.click(screen.getByText('Complete'));
    await waitFor(() =>
      expect(window.localStorage.getItem('goblinos-onboarding-complete')).toBe('true')
    );
    expect(mockPush).toHaveBeenCalledWith('/');
  });

  it('persists completion on skip', async () => {
    render(<OnboardingWizard />, { wrapper });
    fireEvent.click(screen.getByText('Skip'));
    await waitFor(() =>
      expect(window.localStorage.getItem('goblinos-onboarding-complete')).toBe('true')
    );
    expect(mockPush).toHaveBeenCalledWith('/');
  });
});
