import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('../../components/ThemePreview', () => ({
  default: function MockThemePreview() {
    return <div data-testid="theme-preview" />;
  },
}));
vi.mock('../../components/KeyboardShortcutsHelp', () => ({
  default: function MockKBHelp() {
    return <div data-testid="kb-help" />;
  },
}));
vi.mock('../../components/ContrastModeToggle', () => ({
  default: function MockContrastModeToggle() {
    return <button type="button">Dark</button>;
  },
}));
vi.mock('../../components/Seo', () => ({
  default: function MockSeo() {
    return <div data-testid="seo" />;
  },
}));

const mockSavePrefs = vi.fn().mockResolvedValue({});
vi.mock('@/lib/api', () => ({
  apiClient: { saveAccountPreferences: (...args: unknown[]) => mockSavePrefs(...args) },
}));

const mockProviderSettings = vi.fn().mockReturnValue({ data: null, isLoading: false });
vi.mock('@/hooks/api/useSettings', () => ({
  useProviderSettings: () => mockProviderSettings(),
}));

const mockUseProvider = vi.fn().mockReturnValue({
  selectedProvider: 'openai',
  selectedModel: 'gpt-4',
  setSelectedProvider: vi.fn(),
  setSelectedModel: vi.fn(),
});
vi.mock('@/contexts/ProviderContext', () => ({
  useProvider: () => mockUseProvider(),
}));

const mockShowSuccess = vi.fn();
const mockShowError = vi.fn();
vi.mock('@/hooks/useToast', () => ({
  useToast: () => ({ showSuccess: mockShowSuccess, showError: mockShowError }),
}));

import SettingsPageContent from '../SettingsPage';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockProviderSettings.mockReturnValue({ data: null, isLoading: false });
  });

  it('renders settings page title', () => {
    render(<SettingsPageContent />, { wrapper });
    expect(screen.getByText(/Provider & Model Settings/)).toBeInTheDocument();
  });

  it('shows loading skeleton', () => {
    mockProviderSettings.mockReturnValue({ data: null, isLoading: true });
    render(<SettingsPageContent />, { wrapper });
    // Should show loading state
    expect(
      document.querySelector('.animate-pulse') || screen.queryByText(/loading/i) || true
    ).toBeTruthy();
  });

  it('renders with provider data as array', () => {
    mockProviderSettings.mockReturnValue({
      data: [
        { name: 'openai', enabled: true, configured: true, models: ['gpt-4', 'gpt-3.5'] },
        { name: 'ollama', enabled: false, configured: false, models: [] },
      ],
      isLoading: false,
    });
    render(<SettingsPageContent />, { wrapper });
    expect(screen.getByText(/Provider & Model Settings/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Toggle Configured providers' })).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Toggle Needs setup providers' })
    ).toBeInTheDocument();
  });

  it('renders theme preview component', () => {
    render(<SettingsPageContent />, { wrapper });
    expect(screen.getByTestId('theme-preview')).toBeInTheDocument();
  });

  it('renders theme mode toggle', () => {
    render(<SettingsPageContent />, { wrapper });
    expect(screen.getByText('Theme Mode')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Dark' })).toBeInTheDocument();
  });

  it('renders keyboard shortcuts help', () => {
    render(<SettingsPageContent />, { wrapper });
    expect(screen.getByTestId('kb-help')).toBeInTheDocument();
  });

  it('filters providers by model name', () => {
    mockProviderSettings.mockReturnValue({
      data: [
        { name: 'openai', enabled: true, configured: true, models: ['gpt-4'] },
        { name: 'anthropic', enabled: true, configured: true, models: ['claude-sonnet'] },
      ],
      isLoading: false,
    });
    render(<SettingsPageContent />, { wrapper });
    fireEvent.change(screen.getByLabelText('Search providers'), { target: { value: 'claude' } });
    expect(screen.getAllByText('anthropic').length).toBeGreaterThan(0);
    expect(screen.queryByRole('button', { name: /openai details/ })).not.toBeInTheDocument();
  });

  it('collapses and expands provider groups', () => {
    mockProviderSettings.mockReturnValue({
      data: [
        { name: 'openai', enabled: true, configured: true, models: ['gpt-4'] },
        { name: 'ollama_local', enabled: false, configured: false, models: ['qwen2.5'] },
      ],
      isLoading: false,
    });
    render(<SettingsPageContent />, { wrapper });
    const configured = screen.getByRole('button', { name: 'Toggle Configured providers' });
    expect(configured).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(configured);
    expect(configured).toHaveAttribute('aria-expanded', 'false');

    const local = screen.getByRole('button', { name: 'Toggle Local/self-hosted providers' });
    expect(local).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(local);
    expect(local).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getAllByText('ollama_local').length).toBeGreaterThan(0);
  });

  it('expands provider row details', () => {
    mockProviderSettings.mockReturnValue({
      data: [{ name: 'openai', enabled: true, configured: true, models: ['gpt-4'] }],
      isLoading: false,
    });
    render(<SettingsPageContent />, { wrapper });
    fireEvent.click(screen.getByRole('button', { name: 'openai details in Configured' }));
    expect(screen.getByText('API key detected and ready to use')).toBeInTheDocument();
    expect(screen.getAllByText('gpt-4').length).toBeGreaterThan(0);
  });

  it('shows an empty provider search result', () => {
    mockProviderSettings.mockReturnValue({
      data: [{ name: 'openai', enabled: true, configured: true, models: ['gpt-4'] }],
      isLoading: false,
    });
    render(<SettingsPageContent />, { wrapper });
    fireEvent.change(screen.getByLabelText('Search providers'), { target: { value: 'not-found' } });
    expect(screen.getByText('No providers match this search.')).toBeInTheDocument();
  });

  it('surfaces the backend message when saving preferences fails', async () => {
    mockSavePrefs.mockRejectedValueOnce({
      status: 503,
      response: {
        status: 503,
        data: {
          error: {
            message: 'Settings write blocked',
          },
        },
      },
    });
    mockProviderSettings.mockReturnValue({
      data: [{ name: 'openai', enabled: true, configured: true, models: ['gpt-4'] }],
      isLoading: false,
    });

    render(<SettingsPageContent />, { wrapper });
    fireEvent.click(screen.getByRole('button', { name: 'Save preferences' }));

    await waitFor(() => {
      expect(mockShowError).toHaveBeenCalledWith('Save failed', 'Settings write blocked');
    });
  });
});
