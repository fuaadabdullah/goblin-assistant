import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('@/services/raptor', () => ({
  raptorStart: vi.fn().mockResolvedValue({}),
  raptorStop: vi.fn().mockResolvedValue({}),
  raptorStatus: vi.fn().mockResolvedValue({ running: false, config_file: 'test.yaml' }),
  raptorLogs: vi.fn().mockResolvedValue({ log_tail: 'Test log output line 1\nline 2' }),
  raptorDemo: vi.fn().mockResolvedValue({}),
}));

vi.mock('@/components/ui/card', () => ({
  Card: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
  CardContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardTitle: ({ children }: { children: React.ReactNode }) => <h3>{children}</h3>,
}));

vi.mock('@/components/ui/Button', () => ({
  default: function MockButton({
    children,
    onClick,
    disabled,
    ...props
  }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
    return (
      <button onClick={onClick} disabled={disabled} {...props}>
        {children}
      </button>
    );
  },
}));

vi.mock('@/components/ui/Badge', () => ({
  default: function MockBadge({ children }: { children: React.ReactNode }) {
    return <span>{children}</span>;
  },
}));

vi.mock('@/utils/dev-log', () => ({
  devError: vi.fn(),
  devWarn: vi.fn(),
  devLog: vi.fn(),
}));

import RaptorMiniPanel from '../RaptorMiniPanel';
import { raptorStart, raptorStop, raptorStatus, raptorLogs, raptorDemo } from '@/services/raptor';

describe('RaptorMiniPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset to default mock implementations (clearAllMocks doesn't reset these)
    (raptorStatus as vi.Mock).mockResolvedValue({ running: false, config_file: 'test.yaml' });
    (raptorStart as vi.Mock).mockResolvedValue({});
    (raptorStop as vi.Mock).mockResolvedValue({});
    (raptorLogs as vi.Mock).mockResolvedValue({ log_tail: 'Test log output line 1\nline 2' });
    (raptorDemo as vi.Mock).mockResolvedValue({});
  });

  it('renders the panel title', async () => {
    render(<RaptorMiniPanel />);
    expect(screen.getByText('Raptor Mini Demo')).toBeInTheDocument();
    await waitFor(() => {
      expect(raptorStatus).toHaveBeenCalled();
    });
  });

  it('shows status after loading', async () => {
    render(<RaptorMiniPanel />);
    await waitFor(() => {
      expect(screen.getByText(/Running: No/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Config: test.yaml/)).toBeInTheDocument();
  });

  it('starts raptor', async () => {
    (raptorStatus as vi.Mock)
      .mockResolvedValueOnce({ running: false })
      .mockResolvedValueOnce({ running: true });
    render(<RaptorMiniPanel />);
    await waitFor(() => expect(screen.getByText('Start')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Start'));
    await waitFor(() => {
      expect(raptorStart).toHaveBeenCalled();
    });
  });

  it('stops raptor', async () => {
    (raptorStatus as vi.Mock).mockResolvedValue({ running: true });
    render(<RaptorMiniPanel />);
    await waitFor(() => expect(screen.getByText(/Running: Yes/)).toBeInTheDocument());
    fireEvent.click(screen.getByText('Stop'));
    await waitFor(() => {
      expect(raptorStop).toHaveBeenCalled();
    });
  });

  it('fetches logs', async () => {
    render(<RaptorMiniPanel />);
    await waitFor(() => expect(screen.getByText('Fetch Logs')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Fetch Logs'));
    await waitFor(() => {
      expect(raptorLogs).toHaveBeenCalled();
      expect(screen.getByText(/Test log output line 1/)).toBeInTheDocument();
    });
  });

  it('triggers boom demo', async () => {
    render(<RaptorMiniPanel />);
    await waitFor(() => expect(screen.getByText('Trigger Boom')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Trigger Boom'));
    await waitFor(() => {
      expect(raptorDemo).toHaveBeenCalledWith('boom');
    });
  });

  it('shows error on status failure', async () => {
    (raptorStatus as vi.Mock).mockRejectedValueOnce(new Error('fail'));
    render(<RaptorMiniPanel />);
    await waitFor(() => {
      expect(screen.getByText('Failed to fetch status')).toBeInTheDocument();
    });
  });

  it('shows error on start failure', async () => {
    (raptorStart as vi.Mock).mockRejectedValueOnce(new Error('fail'));
    render(<RaptorMiniPanel />);
    await waitFor(() => expect(screen.getByText('Start')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Start'));
    await waitFor(() => {
      expect(screen.getByText('Failed to start raptor')).toBeInTheDocument();
    });
  });

  it('copies logs to clipboard', async () => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
    render(<RaptorMiniPanel />);
    await waitFor(() => expect(screen.getByText('Fetch Logs')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Fetch Logs'));
    await waitFor(() => expect(screen.getByText(/Test log output/)).toBeInTheDocument());
    fireEvent.click(screen.getByLabelText('Copy logs'));
    await waitFor(() => {
      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
        expect.stringContaining('Test log output')
      );
    });
  });
});
