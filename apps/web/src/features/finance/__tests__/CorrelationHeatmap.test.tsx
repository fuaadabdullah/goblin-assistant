import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import CorrelationHeatmap from '../CorrelationHeatmap';

describe('CorrelationHeatmap', () => {
  const mockData = [
    { provider: 'OpenAI', openai: 1.0, anthropic: 0.8, gemini: 0.6 },
    { provider: 'Anthropic', openai: 0.8, anthropic: 1.0, gemini: 0.7 },
    { provider: 'Gemini', openai: 0.6, anthropic: 0.7, gemini: 1.0 },
  ];

  const mockConfig = {
    rowKey: 'provider',
    columns: ['openai', 'anthropic', 'gemini'],
    minValue: 0,
    maxValue: 1.0,
  };

  it('renders heatmap container', () => {
    render(<CorrelationHeatmap title="Provider Correlation" data={mockData} config={mockConfig} />);
    expect(screen.getByText('Provider Correlation')).toBeInTheDocument();
  });

  it('renders title', () => {
    render(<CorrelationHeatmap title="Correlation Matrix" data={mockData} config={mockConfig} />);
    expect(screen.getByText('Correlation Matrix')).toBeInTheDocument();
  });

  it('renders column headers', () => {
    render(<CorrelationHeatmap title="Test" data={mockData} config={mockConfig} />);
    expect(screen.getByText('openai')).toBeInTheDocument();
    expect(screen.getByText('anthropic')).toBeInTheDocument();
    expect(screen.getByText('gemini')).toBeInTheDocument();
  });

  it('renders row headers from data', () => {
    render(<CorrelationHeatmap title="Test" data={mockData} config={mockConfig} />);
    expect(screen.getByText('OpenAI')).toBeInTheDocument();
    expect(screen.getByText('Anthropic')).toBeInTheDocument();
    expect(screen.getByText('Gemini')).toBeInTheDocument();
  });

  it('renders with empty data', () => {
    render(<CorrelationHeatmap title="Test" data={[]} config={mockConfig} />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });

  it('renders table with correct structure', () => {
    const { container } = render(
      <CorrelationHeatmap title="Test" data={mockData} config={mockConfig} />
    );
    const table = container.querySelector('table');
    expect(table).toBeInTheDocument();
    const thead = table?.querySelector('thead');
    expect(thead).toBeInTheDocument();
    const tbody = table?.querySelector('tbody');
    expect(tbody).toBeInTheDocument();
  });
});
