import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('next/dynamic', () => ({
  default: () =>
    function MockLottie() {
      return <div data-testid="lottie" />;
    },
}));
vi.mock('../../hooks/useGoblinLoaderAnimation', () => ({
  __esModule: true,
  default: () => ({ frames: [] }),
}));
// Same convention as ContrastModeToggle.test.tsx: stub lucide so icons are
// queryable by testid.
vi.mock('lucide-react', () => ({
  Brain: (props: Record<string, unknown>) => <span data-testid="icon-Brain" {...props} />,
}));

import ChatEmptyState from '../ChatEmptyState';

const prompts = [
  { label: 'Summarize', prompt: 'Summarize the latest news' },
  { label: 'Code review', prompt: 'Review my pull request' },
  { label: 'Debug', prompt: 'Help me debug this error' },
];

describe('ChatEmptyState', () => {
  const onPromptClick = vi.fn();
  const onModeChange = vi.fn();
  // Prompt cards are drawn from PROMPTS_BY_MODE[selectedMode]; `quickPrompts` is
  // accepted but unused by the component.
  const baseProps = {
    quickPrompts: prompts,
    onPromptClick,
    onModeChange,
    selectedMode: 'all' as const,
  };

  beforeEach(() => vi.clearAllMocks());

  it('renders heading', () => {
    render(<ChatEmptyState {...baseProps} />);
    expect(screen.getByText('What can I help you with?')).toBeInTheDocument();
  });

  it('renders subtitle', () => {
    render(<ChatEmptyState {...baseProps} />);
    expect(screen.getByText(/Choose a suggestion/)).toBeInTheDocument();
  });

  it('renders all quick prompts', () => {
    render(<ChatEmptyState {...baseProps} />);
    expect(screen.getByText('Analyze a stock')).toBeInTheDocument();
    expect(screen.getByText('Explain a concept')).toBeInTheDocument();
    expect(screen.getByText('Run some code')).toBeInTheDocument();
  });

  it('shows prompt text for each card', () => {
    render(<ChatEmptyState {...baseProps} />);
    expect(screen.getByText(/Pull the latest data for AAPL/)).toBeInTheDocument();
    expect(screen.getByText(/Explain present value/)).toBeInTheDocument();
  });

  it('calls onPromptClick with prompt text', () => {
    render(<ChatEmptyState {...baseProps} />);
    fireEvent.click(screen.getByText('Analyze a stock'));
    expect(onPromptClick).toHaveBeenCalledWith(
      'Pull the latest data for AAPL \u2014 price, P/E, recent earnings summary, and analyst consensus.'
    );
  });

  it('calls onPromptClick for different prompts', () => {
    render(<ChatEmptyState {...baseProps} />);
    fireEvent.click(screen.getByText('Run some code'));
    expect(onPromptClick).toHaveBeenCalledWith(
      'Open the Python sandbox and show me how to fetch stock data with yfinance.'
    );
  });

  it('renders lottie animation when not reduced motion', () => {
    render(<ChatEmptyState {...baseProps} />);
    expect(screen.getByTestId('lottie')).toBeInTheDocument();
  });

  it('renders static icon when prefersReducedMotion', () => {
    render(<ChatEmptyState {...baseProps} prefersReducedMotion />);
    expect(screen.queryByTestId('lottie')).not.toBeInTheDocument();
    expect(screen.getByTestId('icon-Brain')).toBeInTheDocument();
  });

  it('renders help text at bottom', () => {
    render(<ChatEmptyState {...baseProps} />);
    expect(screen.getByText(/paste links or attach files/)).toBeInTheDocument();
  });

  it('renders empty state with no prompts', () => {
    render(<ChatEmptyState {...baseProps} quickPrompts={[]} />);
    expect(screen.getByText('What can I help you with?')).toBeInTheDocument();
  });

  it('shows the prompt set for the selected mode', () => {
    render(<ChatEmptyState {...baseProps} selectedMode="finance" />);
    expect(screen.getByText('Analyze a stock')).toBeInTheDocument();
    expect(screen.queryByText('Run some code')).not.toBeInTheDocument();
  });
});
