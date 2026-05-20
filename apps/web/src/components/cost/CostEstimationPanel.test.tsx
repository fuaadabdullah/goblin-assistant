import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

jest.mock('../../hooks/useCostEstimation', () => ({
  __esModule: true,
  useCostEstimation: jest.fn(),
}));

jest.mock('../../hooks/useCostStreaming', () => ({
  __esModule: true,
  useCostStreaming: jest.fn(),
}));

jest.mock('../../hooks/useCostClipboard', () => ({
  __esModule: true,
  useCostClipboard: jest.fn(),
}));

jest.mock('../raptor/RaptorMiniPanel', () => ({
  __esModule: true,
  default: () => <div data-testid="raptor-mini-panel" />,
}));

const mockedUseCostEstimation = require('../../hooks/useCostEstimation').useCostEstimation as jest.Mock;
const mockedUseCostStreaming = require('../../hooks/useCostStreaming').useCostStreaming as jest.Mock;
const mockedUseCostClipboard = require('../../hooks/useCostClipboard').useCostClipboard as jest.Mock;
const CostEstimationPanel = require('./CostEstimationPanel').default as typeof import('./CostEstimationPanel').default;

describe('CostEstimationPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders an empty state when orchestrationText is blank', async () => {
    const resetStreaming = jest.fn();

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
      startStreaming: jest.fn(),
      resetStreaming,
    });

    mockedUseCostClipboard.mockReturnValue({
      copyStatus: null,
      copyFormattedSummary: jest.fn(),
    });

    render(<CostEstimationPanel orchestrationText="" codeInput="" />);

    expect(
      screen.getByText(/Enter an orchestration command to see cost estimates/i)
    ).toBeInTheDocument();

    await waitFor(() => expect(resetStreaming).toHaveBeenCalled());
  });

  it('starts streaming when orchestrationText is provided and no estimate exists yet', async () => {
    const startStreaming = jest.fn();

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
      resetStreaming: jest.fn(),
    });

    mockedUseCostClipboard.mockReturnValue({
      copyStatus: null,
      copyFormattedSummary: jest.fn(),
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
    const startStreaming = jest.fn();
    const copyFormattedSummary = jest.fn();

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
      resetStreaming: jest.fn(),
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
