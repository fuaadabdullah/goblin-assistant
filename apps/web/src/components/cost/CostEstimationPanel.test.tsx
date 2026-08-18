import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

vi.mock('../../hooks/useCostEstimation', () => ({
  useCostEstimation: vi.fn(),
}));

vi.mock('../../hooks/useCostStreaming', () => ({
  useCostStreaming: vi.fn(),
}));

vi.mock('../../hooks/useCostClipboard', () => ({
  useCostClipboard: vi.fn(),
}));

vi.mock('../raptor/RaptorMiniPanel', () => ({
  default: () => <div data-testid="raptor-mini-panel" />,
}));

import { useCostEstimation } from '../../hooks/useCostEstimation';
import { useCostStreaming } from '../../hooks/useCostStreaming';
import { useCostClipboard } from '../../hooks/useCostClipboard';
import CostEstimationPanel from './CostEstimationPanel';

const mockedUseCostEstimation = vi.mocked(useCostEstimation);
const mockedUseCostStreaming = vi.mocked(useCostStreaming);
const mockedUseCostClipboard = vi.mocked(useCostClipboard);

describe('CostEstimationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders an empty state when orchestrationText is blank', async () => {
    const resetStreaming = vi.fn();

    mockedUseCostEstimation.mockReturnValue({
      estimate: null,
      loading: false,
      error: null,
      rateLimitInfo: null,
    });

    mockedUseCostStreaming.mockReturnValue({
      streamLines: [],
      streaming: false,
      showSummary: false,
      startStreaming: vi.fn(),
      resetStreaming,
    });

    mockedUseCostClipboard.mockReturnValue({
      copyStatus: null,
      copyFormattedSummary: vi.fn(),
    });

    render(<CostEstimationPanel orchestrationText="" codeInput="" />);

    expect(
      screen.getByText(/Enter an orchestration command to see cost estimates/i)
    ).toBeInTheDocument();

    await waitFor(() => expect(resetStreaming).toHaveBeenCalled());
  });

  it('starts streaming when orchestrationText is provided and no estimate exists yet', async () => {
    const startStreaming = vi.fn();

    mockedUseCostEstimation.mockReturnValue({
      estimate: null,
      loading: false,
      error: null,
      rateLimitInfo: null,
    });

    mockedUseCostStreaming.mockReturnValue({
      streamLines: ['Analyzing orchestration...'],
      streaming: true,
      showSummary: false,
      startStreaming,
      resetStreaming: vi.fn(),
    });

    mockedUseCostClipboard.mockReturnValue({
      copyStatus: null,
      copyFormattedSummary: vi.fn(),
    });

    render(
      <CostEstimationPanel
        orchestrationText="run something"
        codeInput="console.log('hi')"
        provider="openai"
        model="gpt-4o-mini"
      />
    );

    await waitFor(() =>
      expect(startStreaming).toHaveBeenCalledWith(
        'run something',
        "console.log('hi')",
        'openai',
        'gpt-4o-mini'
      )
    );

    expect(screen.getByText(/Live Estimation/i)).toBeInTheDocument();
    expect(screen.getByText(/Analyzing orchestration/i)).toBeInTheDocument();
  });

  it('shows summary and cost display when estimate is available, and allows copy', async () => {
    const startStreaming = vi.fn();
    const copyFormattedSummary = vi.fn();

    const estimate = {
      estimatedCost: 0.0123,
      estimatedTokens: 123,
      provider: 'openai',
      model: 'gpt-4o-mini',
      breakdown: [{ label: 'Estimated total', cost: 0.0123, tokens: 123 }],
    };

    mockedUseCostEstimation.mockReturnValue({
      estimate,
      loading: false,
      error: null,
      rateLimitInfo: { remaining: 10, limit: 120, resetSeconds: 60 },
    });

    mockedUseCostStreaming.mockReturnValue({
      streamLines: [],
      streaming: false,
      showSummary: true,
      startStreaming,
      resetStreaming: vi.fn(),
    });

    mockedUseCostClipboard.mockReturnValue({
      copyStatus: null,
      copyFormattedSummary,
    });

    render(<CostEstimationPanel orchestrationText="run something" codeInput="" />);

    await waitFor(() => expect(startStreaming).not.toHaveBeenCalled());

    expect(screen.getByRole('heading', { name: 'Summary' })).toBeInTheDocument();
    expect(
      screen.getByText((_, node) => node?.textContent === 'Estimated cost: $0.0123')
    ).toBeInTheDocument();
    expect(screen.getByText(/Estimated tokens: 123/i)).toBeInTheDocument();

    expect(screen.getByText(/Total Estimated Cost/i)).toBeInTheDocument();
    expect(screen.getAllByText('$0.0123').length).toBeGreaterThan(0);

    const copyBtn = screen.getByRole('button', { name: /Copy summary/i });
    fireEvent.click(copyBtn);
    expect(copyFormattedSummary).toHaveBeenCalledWith(estimate);
  });
});
