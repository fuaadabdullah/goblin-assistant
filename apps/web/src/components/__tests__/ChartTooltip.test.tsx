import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import ChartTooltip from '../common/ChartTooltip';

describe('ChartTooltip', () => {
  it('returns null when active is false', () => {
    const { container } = render(
      <ChartTooltip active={false} payload={[{ value: 100 }]} label="Jan" />
    );
    expect(container.firstChild).toBeNull();
  });

  it('returns null when payload is empty', () => {
    const { container } = render(<ChartTooltip active={true} payload={[]} label="Jan" />);
    expect(container.firstChild).toBeNull();
  });

  it('returns null when payload is undefined', () => {
    const { container } = render(<ChartTooltip active={true} label="Jan" />);
    expect(container.firstChild).toBeNull();
  });

  it('renders the label', () => {
    render(<ChartTooltip active={true} payload={[{ value: 100 }]} label="January" />);
    // Appears both as the label header and as the fallback series name
    const labels = screen.getAllByText('January');
    expect(labels.length).toBe(2);
  });

  it('renders series name from entry.name', () => {
    render(<ChartTooltip active={true} payload={[{ name: 'Revenue', value: 500 }]} label="Q1" />);
    expect(screen.getByText('Revenue')).toBeInTheDocument();
  });

  it('renders series name from dataKey when name is absent', () => {
    render(<ChartTooltip active={true} payload={[{ dataKey: 'sales', value: 200 }]} />);
    expect(screen.getByText('sales')).toBeInTheDocument();
  });

  it('renders the value', () => {
    render(<ChartTooltip active={true} payload={[{ name: 'Sales', value: 150 }]} />);
    expect(screen.getByText('150')).toBeInTheDocument();
  });

  it('renders multiple payload entries', () => {
    render(
      <ChartTooltip
        active={true}
        payload={[
          { name: 'Revenue', value: 300 },
          { name: 'Cost', value: 100 },
        ]}
        label="2024"
      />
    );
    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('Cost')).toBeInTheDocument();
    expect(screen.getByText('300')).toBeInTheDocument();
    expect(screen.getByText('100')).toBeInTheDocument();
  });

  it('does not render label when label is undefined', () => {
    const { container } = render(
      <ChartTooltip active={true} payload={[{ name: 'Test', value: 1 }]} />
    );
    expect(container.querySelector('.font-medium')).toBeNull();
  });
});
