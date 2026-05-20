import { render, screen } from '@testing-library/react';
import ProviderUsageChart from '../ProviderUsageChart';

describe('ProviderUsageChart', () => {
  it('renders request charts without approximation copy', () => {
    render(
      <ProviderUsageChart
        metric="requests"
        data={[
          { name: 'openai', value: 12 },
          { name: 'anthropic', value: 8 },
        ]}
      />
    );

    expect(screen.getByRole('heading', { name: 'Provider Requests' })).toBeInTheDocument();
    expect(screen.queryByText(/Approximated/i)).not.toBeInTheDocument();
  });

  it('renders a cost fallback title when request counts are unavailable', () => {
    render(
      <ProviderUsageChart
        metric="cost"
        data={[
          { name: 'openai', value: 1.23 },
          { name: 'anthropic', value: 0.45 },
        ]}
      />
    );

    expect(screen.getByRole('heading', { name: 'Provider Costs' })).toBeInTheDocument();
  });
});
