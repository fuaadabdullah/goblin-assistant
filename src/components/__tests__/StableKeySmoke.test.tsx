import { fireEvent, render, screen } from '@testing-library/react';
import HealthCard from '../HealthCard';
import StatusCard from '../StatusCard';
import ChartTooltip from '../common/ChartTooltip';

describe('stable key smoke coverage', () => {
  it('renders HealthCard metrics and recent errors after expand', () => {
    render(
      <HealthCard
        title="Gateway"
        status="degraded"
        icon="G"
        metrics={[
          { label: 'Latency', value: '120 ms' },
          { label: 'Requests', value: 42 },
        ]}
        errors={[
          { timestamp: '2026-03-09T12:00:00.000Z', message: 'Timed out' },
          { timestamp: '2026-03-09T12:01:00.000Z', message: 'Rate limited' },
        ]}
      />
    );

    fireEvent.click(screen.getByRole('button'));

    expect(screen.getByText('Latency')).toBeInTheDocument();
    expect(screen.getByText('120 ms')).toBeInTheDocument();
    expect(screen.getByText('Timed out')).toBeInTheDocument();
    expect(screen.getByText('Rate limited')).toBeInTheDocument();
  });

  it('renders StatusCard metadata without changing visible output', () => {
    render(
      <StatusCard
        title="Inference API"
        status="healthy"
        icon="I"
        meta={[
          { label: 'Provider', value: 'OpenAI' },
          { label: 'Region', value: 'iad' },
        ]}
      />
    );

    expect(screen.getByText('Inference API')).toBeInTheDocument();
    expect(screen.getByText('Provider')).toBeInTheDocument();
    expect(screen.getByText('OpenAI')).toBeInTheDocument();
    expect(screen.getByText('Region')).toBeInTheDocument();
    expect(screen.getByText('iad')).toBeInTheDocument();
  });

  it('renders ChartTooltip rows for active payloads', () => {
    render(
      <ChartTooltip
        active={true}
        label="Latency"
        payload={[
          { name: 'p95', value: '320 ms' },
          { dataKey: 'p99', value: '540 ms' },
        ]}
      />
    );

    expect(screen.getByText('Latency')).toBeInTheDocument();
    expect(screen.getByText('p95')).toBeInTheDocument();
    expect(screen.getByText('320 ms')).toBeInTheDocument();
    expect(screen.getByText('p99')).toBeInTheDocument();
    expect(screen.getByText('540 ms')).toBeInTheDocument();
  });
});
