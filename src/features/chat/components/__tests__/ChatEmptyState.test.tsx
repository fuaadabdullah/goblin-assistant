import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';

jest.mock('next/dynamic', () => () => {
  return function MockLottie() {
    return <div data-testid="lottie" />;
  };
});
jest.mock('../../hooks/useGoblinLoaderAnimation', () => ({
  __esModule: true,
  default: () => ({ frames: [] }),
}));

import ChatEmptyState from '../ChatEmptyState';

const prompts = [
  { label: 'Summarize', prompt: 'Summarize the latest news' },
  { label: 'Code review', prompt: 'Review my pull request' },
  { label: 'Debug', prompt: 'Help me debug this error' },
];

describe('ChatEmptyState', () => {
  const onPromptClick = jest.fn();

  beforeEach(() => jest.clearAllMocks());

  it('renders heading', () => {
    render(<ChatEmptyState quickPrompts={prompts} onPromptClick={onPromptClick} />);
    expect(screen.getByText('What can I help you with?')).toBeInTheDocument();
  });

  it('renders subtitle', () => {
    render(<ChatEmptyState quickPrompts={prompts} onPromptClick={onPromptClick} />);
    expect(screen.getByText(/Choose a suggestion/)).toBeInTheDocument();
  });

  it('renders all quick prompts', () => {
    render(<ChatEmptyState quickPrompts={prompts} onPromptClick={onPromptClick} />);
    expect(screen.getByText('Summarize')).toBeInTheDocument();
    expect(screen.getByText('Code review')).toBeInTheDocument();
    expect(screen.getByText('Debug')).toBeInTheDocument();
  });

  it('shows prompt text for each card', () => {
    render(<ChatEmptyState quickPrompts={prompts} onPromptClick={onPromptClick} />);
    expect(screen.getByText('Summarize the latest news')).toBeInTheDocument();
    expect(screen.getByText('Review my pull request')).toBeInTheDocument();
  });

  it('calls onPromptClick with prompt text', () => {
    render(<ChatEmptyState quickPrompts={prompts} onPromptClick={onPromptClick} />);
    fireEvent.click(screen.getByText('Summarize'));
    expect(onPromptClick).toHaveBeenCalledWith('Summarize the latest news');
  });

  it('calls onPromptClick for different prompts', () => {
    render(<ChatEmptyState quickPrompts={prompts} onPromptClick={onPromptClick} />);
    fireEvent.click(screen.getByText('Debug'));
    expect(onPromptClick).toHaveBeenCalledWith('Help me debug this error');
  });

  it('renders lottie animation when not reduced motion', () => {
    render(<ChatEmptyState quickPrompts={prompts} onPromptClick={onPromptClick} />);
    expect(screen.getByTestId('lottie')).toBeInTheDocument();
  });

  it('renders static icon when prefersReducedMotion', () => {
    render(<ChatEmptyState quickPrompts={prompts} onPromptClick={onPromptClick} prefersReducedMotion />);
    expect(screen.queryByTestId('lottie')).not.toBeInTheDocument();
    expect(screen.getByText('🧠')).toBeInTheDocument();
  });

  it('renders help text at bottom', () => {
    render(<ChatEmptyState quickPrompts={prompts} onPromptClick={onPromptClick} />);
    expect(screen.getByText(/paste links or attach files/)).toBeInTheDocument();
  });

  it('renders empty state with no prompts', () => {
    render(<ChatEmptyState quickPrompts={[]} onPromptClick={onPromptClick} />);
    expect(screen.getByText('What can I help you with?')).toBeInTheDocument();
  });
});
