import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('@/lib/api/runtimeClient', () => ({
  runtimeClient: {
    setProviderApiKey: vi.fn(),
    getApiKey: vi.fn(),
    clearApiKey: vi.fn(),
  },
}));

import APIKeyManager from '../APIKeyManager';
import { runtimeClient } from '@/lib/api/runtimeClient';

const mockSetKey = runtimeClient.setProviderApiKey as vi.Mock;
const mockGetKey = runtimeClient.getApiKey as vi.Mock;
const mockClearKey = runtimeClient.clearApiKey as vi.Mock;

const defaultProps = {
  providers: ['openai', 'anthropic', 'google'],
  selectedProvider: 'openai',
  onProviderChange: vi.fn(),
};

describe('APIKeyManager', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders heading', () => {
    render(<APIKeyManager {...defaultProps} />);
    expect(screen.getByText('API Keys (secure)')).toBeInTheDocument();
  });

  it('renders provider select with all providers', () => {
    render(<APIKeyManager {...defaultProps} />);
    const select = screen.getByLabelText('Provider') as HTMLSelectElement;
    expect(select.value).toBe('openai');
    expect(screen.getByText('anthropic')).toBeInTheDocument();
    expect(screen.getByText('google')).toBeInTheDocument();
  });

  it('calls onProviderChange when select changes', async () => {
    const user = userEvent.setup();
    render(<APIKeyManager {...defaultProps} />);
    await user.selectOptions(screen.getByLabelText('Provider'), 'anthropic');
    expect(defaultProps.onProviderChange).toHaveBeenCalledWith('anthropic');
  });

  it('renders password input for key', () => {
    render(<APIKeyManager {...defaultProps} />);
    const input = screen.getByLabelText('Key') as HTMLInputElement;
    expect(input.type).toBe('password');
  });

  it('save button is disabled when key is empty', () => {
    render(<APIKeyManager {...defaultProps} />);
    expect(screen.getByText('Save')).toBeDisabled();
  });

  it('saves key successfully', async () => {
    mockSetKey.mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<APIKeyManager {...defaultProps} />);
    await user.type(screen.getByLabelText('Key'), 'sk-test-123');
    await user.click(screen.getByText('Save'));
    await waitFor(() => {
      expect(mockSetKey).toHaveBeenCalledWith('openai', 'sk-test-123');
      expect(screen.getByText('Saved securely')).toBeInTheDocument();
    });
  });

  it('shows error on save failure', async () => {
    mockSetKey.mockRejectedValue(new Error('network error'));
    const user = userEvent.setup();
    render(<APIKeyManager {...defaultProps} />);
    await user.type(screen.getByLabelText('Key'), 'bad-key');
    await user.click(screen.getByText('Save'));
    await waitFor(() => {
      expect(screen.getByText('Failed to save: network error')).toBeInTheDocument();
    });
  });

  it('checks key status', async () => {
    mockGetKey.mockResolvedValue('sk-***');
    const user = userEvent.setup();
    render(<APIKeyManager {...defaultProps} />);
    await user.click(screen.getByText('Check'));
    await waitFor(() => {
      expect(mockGetKey).toHaveBeenCalledWith('openai');
      expect(screen.getByText('Key present')).toBeInTheDocument();
    });
  });

  it('shows no key stored when key is empty', async () => {
    mockGetKey.mockResolvedValue(null);
    const user = userEvent.setup();
    render(<APIKeyManager {...defaultProps} />);
    await user.click(screen.getByText('Check'));
    await waitFor(() => {
      expect(screen.getByText('No key stored')).toBeInTheDocument();
    });
  });

  it('shows error on check failure', async () => {
    mockGetKey.mockRejectedValue(new Error('timeout'));
    const user = userEvent.setup();
    render(<APIKeyManager {...defaultProps} />);
    await user.click(screen.getByText('Check'));
    await waitFor(() => {
      expect(screen.getByText('Failed to read: timeout')).toBeInTheDocument();
    });
  });

  it('clears key successfully', async () => {
    mockClearKey.mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<APIKeyManager {...defaultProps} />);
    await user.click(screen.getByText('Clear'));
    await waitFor(() => {
      expect(mockClearKey).toHaveBeenCalledWith('openai');
      expect(screen.getByText('Cleared')).toBeInTheDocument();
    });
  });

  it('shows error on clear failure', async () => {
    mockClearKey.mockRejectedValue(new Error('forbidden'));
    const user = userEvent.setup();
    render(<APIKeyManager {...defaultProps} />);
    await user.click(screen.getByText('Clear'));
    await waitFor(() => {
      expect(screen.getByText('Failed to clear: forbidden')).toBeInTheDocument();
    });
  });

  it('does not render status when empty', () => {
    render(<APIKeyManager {...defaultProps} />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});
