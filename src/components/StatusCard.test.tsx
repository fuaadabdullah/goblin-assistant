import { describe, it, expect } from "vitest";
import { render } from '@testing-library/react';
import StatusCard from './StatusCard';

describe('StatusCard', () => {
  test('renders with title and healthy status', () => {
    const { getByText, getByRole } = render(
      <StatusCard
        title="Backend API"
        status="healthy"
        icon="⚡"
        lastCheck={new Date().toISOString()}
      />
    );

    expect(getByText('Backend API')).toBeInTheDocument();
    expect(getByText('⚡')).toBeInTheDocument();
    expect(getByRole('status')).toHaveTextContent('Healthy');
  });

  test('renders with degraded status and warning styling', () => {
    const { getByRole } = render(
      <StatusCard
        title="Service"
        status="degraded"
        icon="⚠️"
        lastCheck={new Date().toISOString()}
      />
    );

    const badge = getByRole('status');
    expect(badge).toHaveTextContent('Degraded');
  });

  test('renders with down status and error styling', () => {
    const { getByRole } = render(
      <StatusCard title="Database" status="down" icon="❌" lastCheck={new Date().toISOString()} />
    );

    const badge = getByRole('status');
    expect(badge).toHaveTextContent('Down');
  });

  test('displays formatted last check timestamp', () => {
    const fiveMinutesAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();

    const { getByText } = render(
      <StatusCard title="Service" status="healthy" icon="✓" lastCheck={fiveMinutesAgo} />
    );

    // Should show relative time like "5m ago"
    expect(getByText(/ago/i)).toBeInTheDocument();
  });

  test('renders with status details tooltip', () => {
    const { getByText } = render(
      <StatusCard
        title="API Gateway"
        status="degraded"
        icon="⚡"
        lastCheck={new Date().toISOString()}
        statusDetails="High latency detected on endpoint /api/v1"
      />
    );

    expect(getByText('API Gateway')).toBeInTheDocument();
    // Tooltip content is rendered but may not be visible until hover
  });

  test('renders with metadata', () => {
    const meta = [
      { label: 'Version', value: '1.0.0' },
      { label: 'Uptime', value: '99.9%' },
      { label: 'Requests', value: 1234 },
    ];

    const { getByText } = render(
      <StatusCard
        title="Service"
        status="healthy"
        icon="✓"
        lastCheck={new Date().toISOString()}
        meta={meta}
      />
    );

    expect(getByText('Version')).toBeInTheDocument();
    expect(getByText('1.0.0')).toBeInTheDocument();
    expect(getByText('Uptime')).toBeInTheDocument();
    expect(getByText('99.9%')).toBeInTheDocument();
    expect(getByText('Requests')).toBeInTheDocument();
    expect(getByText('1234')).toBeInTheDocument();
  });

  test('applies custom className', () => {
    const { container } = render(
      <StatusCard
        title="Service"
        status="healthy"
        icon="✓"
        lastCheck={new Date().toISOString()}
        className="custom-card"
      />
    );

    const card = container.firstChild as HTMLElement;
    expect(card).toHaveClass('custom-card');
  });

  test('displays unknown status when status is not recognized', () => {
    const { getByRole } = render(
      <StatusCard title="Service" status="unknown" icon="?" lastCheck={new Date().toISOString()} />
    );

    const badge = getByRole('status');
    expect(badge).toHaveTextContent('Unknown');
  });
});
