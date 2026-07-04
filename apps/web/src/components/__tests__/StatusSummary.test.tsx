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

  it('shows connected status after health resolves successfully', () => {
    render(
      <StatusSummary
        chatTestResult={{ status: 'ok' }}
        chatError={null}
        health={{ isLoading: false, isError: false }}
        isAuthenticated={true}
      />
    );

    expect(screen.getAllByText('✓ Connected')).toHaveLength(2);
    expect(screen.getByText('✓ Authenticated')).toBeInTheDocument();
  });
});
