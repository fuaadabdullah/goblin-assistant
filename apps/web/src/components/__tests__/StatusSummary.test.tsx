import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import StatusSummary from '../../../app/debug/connectivity/components/StatusSummary';

describe('StatusSummary', () => {
  it('shows backend loading and chat failure states', () => {
    render(
      <StatusSummary
        chatTestResult={null}
        chatError="Valid API key required"
        health={{ isLoading: true, isError: false }}
        isAuthenticated={false}
      />
    );

    expect(screen.getByText('… Loading')).toBeInTheDocument();
    expect(screen.getByText('✗ Failed')).toBeInTheDocument();
    expect(screen.getByText('⚠ Not authenticated')).toBeInTheDocument();
  });

  it('does not label expected chat auth failures as API outages', () => {
    render(
      <StatusSummary
        chatTestResult={null}
        chatError="Not authenticated"
        health={{ isLoading: false, isError: false }}
        isAuthenticated={false}
      />
    );

    expect(screen.getByText('⚠ Authentication required')).toBeInTheDocument();
    expect(screen.queryByText('✗ Failed')).not.toBeInTheDocument();
  });

  it('shows healthy status when backend health is healthy', () => {
    render(
      <StatusSummary
        chatTestResult={{ status: 'ok' }}
        chatError={null}
        health={{
          isLoading: false,
          isError: false,
          data: { overall: 'healthy', timestamp: '2026-07-04T00:00:00Z', services: {} },
        }}
        isAuthenticated={true}
      />
    );

    expect(screen.getAllByText('✓ Connected')).toHaveLength(2);
    expect(screen.getByText('✓ Authenticated')).toBeInTheDocument();
  });

  it('shows unknown status when health payload is not healthy', () => {
    render(
      <StatusSummary
        chatTestResult={null}
        chatError={null}
        health={{
          isLoading: false,
          isError: false,
          data: { overall: 'unknown', timestamp: '2026-07-04T00:00:00Z', services: {} },
        }}
        isAuthenticated={false}
      />
    );

    expect(screen.getByText('⚠ Unknown')).toBeInTheDocument();
  });
});
