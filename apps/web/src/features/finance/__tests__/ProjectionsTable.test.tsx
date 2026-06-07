import React from 'react';
import { render, screen } from '@testing-library/react';
import ProjectionsTable from '../ProjectionsTable';

describe('ProjectionsTable', () => {
  const mockData = [
    { provider: 'OpenAI', q1: 100, q2: 120, q3: 140, q4: 160 },
    { provider: 'Anthropic', q1: 80, q2: 90, q3: 100, q4: 110 },
    { provider: 'Gemini', q1: 60, q2: 70, q3: 80, q4: 90 },
  ];

  const mockConfig = {
    columns: [
      { key: 'provider', label: 'Provider' },
      { key: 'q1', label: 'q1' },
      { key: 'q2', label: 'q2' },
      { key: 'q3', label: 'q3' },
      { key: 'q4', label: 'q4' },
    ],
  };

  it('renders table', () => {
    const { container } = render(
      <ProjectionsTable title="Cost Projections" data={mockData} config={mockConfig} />
    );
    expect(container.querySelector('table')).toBeInTheDocument();
  });

  it('renders title', () => {
    render(<ProjectionsTable title="Cost Projections" data={mockData} config={mockConfig} />);
    expect(screen.getByText('Cost Projections')).toBeInTheDocument();
  });

  it('renders column headers', () => {
    render(<ProjectionsTable title="Test" data={mockData} config={mockConfig} />);
    expect(screen.getByText('q1')).toBeInTheDocument();
    expect(screen.getByText('q2')).toBeInTheDocument();
    expect(screen.getByText('q3')).toBeInTheDocument();
    expect(screen.getByText('q4')).toBeInTheDocument();
  });

  it('renders row data', () => {
    render(<ProjectionsTable title="Test" data={mockData} config={mockConfig} />);
    expect(screen.getByText('OpenAI')).toBeInTheDocument();
    expect(screen.getByText('Anthropic')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    render(<ProjectionsTable title="Test" data={[]} config={mockConfig} />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});
