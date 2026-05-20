import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('../Card', () => {
  return function MockCard({ children, className, ...props }: { children: React.ReactNode; className?: string; [k: string]: unknown }) {
    return <div data-testid="card" className={className} {...props}>{children}</div>;
  };
});

jest.mock('../ui/Badge', () => {
  return function MockBadge({ children, icon, variant, ...props }: { children: React.ReactNode; icon?: string; variant?: string; [k: string]: unknown }) {
    return <span data-testid="badge" data-variant={variant} {...props}>{icon} {children}</span>;
  };
});

jest.mock('../ui/Tooltip', () => {
  return function MockTooltip({ children, content }: { children: React.ReactNode; content: string }) {
    return <div data-testid="tooltip" title={content}>{children}</div>;
  };
});

import StatusCard from '../StatusCard';

describe('StatusCard', () => {
  it('renders the title', () => {
    render(<StatusCard title="Backend API" status="healthy" />);
    expect(screen.getByText('Backend API')).toBeInTheDocument();
  });

  it('renders healthy badge', () => {
    render(<StatusCard title="Test" status="healthy" />);
    expect(screen.getByText(/Healthy/)).toBeInTheDocument();
  });

  it('renders degraded badge', () => {
    render(<StatusCard title="Test" status="degraded" />);
    expect(screen.getByText(/Degraded/)).toBeInTheDocument();
  });

  it('renders down badge', () => {
    render(<StatusCard title="Test" status="down" />);
    expect(screen.getByText(/Down/)).toBeInTheDocument();
  });

  it('renders unknown badge', () => {
    render(<StatusCard title="Test" status="unknown" />);
    expect(screen.getByText(/Unknown/)).toBeInTheDocument();
  });

  it('renders meta items', () => {
    render(
      <StatusCard
        title="Test"
        status="healthy"
        meta={[
          { label: 'Latency', value: '50 ms' },
          { label: 'Requests', value: 1000 },
        ]}
      />
    );
    expect(screen.getByText('Latency')).toBeInTheDocument();
    expect(screen.getByText('50 ms')).toBeInTheDocument();
    expect(screen.getByText('Requests')).toBeInTheDocument();
    expect(screen.getByText('1000')).toBeInTheDocument();
  });

  it('does not render meta section when empty', () => {
    const { container } = render(<StatusCard title="Test" status="healthy" />);
    expect(container.querySelector('.grid')).not.toBeInTheDocument();
  });

  it('renders icon when provided', () => {
    render(<StatusCard title="Test" status="healthy" icon={<span data-testid="icon">🔧</span>} />);
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });

  it('shows "Just now" for recent lastCheck', () => {
    const now = new Date().toISOString();
    render(<StatusCard title="Test" status="healthy" lastCheck={now} />);
    expect(screen.getByText('Just now')).toBeInTheDocument();
  });

  it('shows minutes ago for lastCheck within an hour', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    render(<StatusCard title="Test" status="healthy" lastCheck={fiveMinAgo} />);
    expect(screen.getByText('5m ago')).toBeInTheDocument();
  });

  it('shows hours ago for lastCheck within a day', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    render(<StatusCard title="Test" status="healthy" lastCheck={twoHoursAgo} />);
    expect(screen.getByText('2h ago')).toBeInTheDocument();
  });

  it('does not show timeAgo when lastCheck is not provided', () => {
    render(<StatusCard title="Test" status="healthy" />);
    expect(screen.queryByText(/ago|Just now/)).not.toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<StatusCard title="Test" status="healthy" className="my-card" />);
    const card = screen.getByTestId('card');
    expect(card.className).toContain('my-card');
  });

  it('sets aria-label with title and status description', () => {
    render(<StatusCard title="MyService" status="healthy" />);
    const group = screen.getByRole('group');
    expect(group.getAttribute('aria-label')).toContain('MyService');
    expect(group.getAttribute('aria-label')).toContain('Healthy');
  });

  it('uses statusDetails for tooltip when provided', () => {
    render(<StatusCard title="Test" status="healthy" statusDetails="All good" />);
    const tooltip = screen.getByTestId('tooltip');
    expect(tooltip.title).toBe('All good');
  });

  it('uses default description for tooltip when no statusDetails', () => {
    render(<StatusCard title="Test" status="healthy" />);
    const tooltip = screen.getByTestId('tooltip');
    expect(tooltip.title).toContain('operational');
  });

  it('applies success border for healthy', () => {
    render(<StatusCard title="Test" status="healthy" />);
    const card = screen.getByTestId('card');
    expect(card.className).toContain('border-success');
  });

  it('applies warning border for degraded', () => {
    render(<StatusCard title="Test" status="degraded" />);
    const card = screen.getByTestId('card');
    expect(card.className).toContain('border-warning');
  });

  it('applies danger border for down', () => {
    render(<StatusCard title="Test" status="down" />);
    const card = screen.getByTestId('card');
    expect(card.className).toContain('border-danger');
  });
});
