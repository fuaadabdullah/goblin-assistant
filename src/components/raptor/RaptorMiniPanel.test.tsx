import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import RaptorMiniPanel from './RaptorMiniPanel';

// Mock API client functions used by the component
vi.mock('../../api/api-client', () => ({
  raptorStart: vi.fn(async () => ({ running: true })),
  raptorStop: vi.fn(async () => ({ running: false })),
  raptorStatus: vi.fn(async () => ({ running: false, config_file: 'config/test.ini' })),
  raptorLogs: vi.fn(async () => ({ log_tail: 'line1\nline2' })),
  raptorDemo: vi.fn(async () => ({ result: 'boom' })),
}));

import * as apiClient from '@/api/api-client';

const mockedClient = vi.mocked(apiClient);

describe('RaptorMiniPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches and displays status on mount', async () => {
    render(<RaptorMiniPanel />);
    await waitFor(() => expect(mockedClient.raptorStatus).toHaveBeenCalled());
    expect(screen.getByText(/Config: config\/test.ini/i)).toBeInTheDocument();
  });

  it('calls start and updates status', async () => {
    render(<RaptorMiniPanel />);
    const startBtn = screen.getByRole('button', { name: /Start/i });
    fireEvent.click(startBtn);
    await waitFor(() => expect(mockedClient.raptorStart).toHaveBeenCalled());
  });

  it('calls stop', async () => {
    // Mock status to show raptor is running
    mockedClient.raptorStatus.mockResolvedValueOnce({
      running: true,
      config_file: 'config/test.ini',
    });

    render(<RaptorMiniPanel />);

    // Wait for status to be loaded (showing running: true)
    await waitFor(() => {
      expect(screen.getByText('Running: Yes')).toBeInTheDocument();
    });

    const stopBtn = screen.getByRole('button', { name: /Stop/i });
    fireEvent.click(stopBtn);
    await waitFor(() => expect(mockedClient.raptorStop).toHaveBeenCalled());
  });

  it('fetches logs and displays them', async () => {
    render(<RaptorMiniPanel />);
    const fetchBtn = screen.getByRole('button', { name: /Fetch Logs/i });
    fireEvent.click(fetchBtn);
    await waitFor(() => expect(mockedClient.raptorLogs).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(/line1/)).toBeInTheDocument());
  });

  it('runs demo and fetches logs', async () => {
    render(<RaptorMiniPanel />);
    const demoBtn = screen.getByRole('button', { name: /Trigger Boom/i });
    fireEvent.click(demoBtn);
    await waitFor(() => expect(mockedClient.raptorDemo).toHaveBeenCalledWith('boom'));
    await waitFor(() => expect(mockedClient.raptorLogs).toHaveBeenCalled());
  });

  it('copies logs when copy button is pressed', async () => {
    const originalNavigator = (globalThis as { navigator?: { clipboard?: { writeText: unknown } } })
      .navigator;
    const writeSpy = vi.fn();
    (globalThis as { navigator: { clipboard: { writeText: unknown } } }).navigator = {
      clipboard: { writeText: writeSpy },
    };

    render(<RaptorMiniPanel />);
    const fetchBtn = screen.getByRole('button', { name: /Fetch Logs/i });
    fireEvent.click(fetchBtn);
    await waitFor(() => expect(screen.getByText(/line1/)).toBeInTheDocument());

    const copyBtn = screen.getByRole('button', { name: /Copy logs/i });
    fireEvent.click(copyBtn);
    expect(writeSpy).toHaveBeenCalled();

    if (originalNavigator) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (globalThis as any).navigator = originalNavigator;
    }
  });
});
