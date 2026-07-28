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

describe('OnboardingWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
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
    await waitFor(() => expect(localStorage.getItem('goblinos-onboarding-complete')).toBe('true'));
    expect(mockPush).toHaveBeenCalledWith('/');
  });

  it('persists completion on skip', async () => {
    render(<OnboardingWizard />, { wrapper });
    fireEvent.click(screen.getByText('Skip'));
    await waitFor(() => expect(localStorage.getItem('goblinos-onboarding-complete')).toBe('true'));
    expect(mockPush).toHaveBeenCalledWith('/');
  });
});
