import React from 'react';
import { render, screen } from '@testing-library/react';

jest.mock('next/dynamic', () => () => function MockLottie() {
  return <div data-testid="lottie" />;
});
jest.mock('../../hooks/useGoblinLoaderAnimation', () => ({
  __esModule: true,
  default: () => ({ mock: 'animation-data' }),
}));
jest.mock('../MessageMarkdown', () => function MockMarkdown({ content }: { content: string }) {
  return <div data-testid="message-markdown">{content}</div>;
});

import StreamingMessage from '../StreamingMessage';

describe('StreamingMessage', () => {
  const baseMessage = {
    id: '1',
    createdAt: '2024-01-01T00:00:00Z',
    role: 'assistant' as const,
    content: 'Hello world',
  };

  it('renders message content via MessageMarkdown', () => {
    render(<StreamingMessage message={baseMessage} isStreaming={false} />);
    expect(screen.getByTestId('message-markdown')).toHaveTextContent('Hello world');
  });

  it('does not show streaming indicator when not streaming', () => {
    const { container } = render(<StreamingMessage message={baseMessage} isStreaming={false} />);
    expect(container.querySelector('.animate-bounce')).not.toBeInTheDocument();
  });

  it('shows streaming indicator when streaming', () => {
    const { container } = render(<StreamingMessage message={baseMessage} isStreaming={true} />);
    expect(container.querySelector('.animate-bounce')).toBeInTheDocument();
  });

  it('shows Generating text when prefers reduced motion', () => {
    render(<StreamingMessage message={baseMessage} isStreaming={true} prefersReducedMotion />);
    expect(screen.getByText('Generating...')).toBeInTheDocument();
  });

  it('does not show bounce dots when prefers reduced motion', () => {
    const { container } = render(
      <StreamingMessage message={baseMessage} isStreaming={true} prefersReducedMotion />,
    );
    expect(container.querySelector('.animate-bounce')).not.toBeInTheDocument();
  });

  it('does not show Generating text when prefers reduced motion is false and animation data exists', () => {
    render(<StreamingMessage message={baseMessage} isStreaming={true} prefersReducedMotion={false} />);
    expect(screen.queryByText('Generating...')).not.toBeInTheDocument();
  });

  it('renders empty content message', () => {
    render(<StreamingMessage message={{ ...baseMessage, content: '' }} isStreaming={true} />);
    expect(screen.getByTestId('message-markdown')).toBeInTheDocument();
  });
});
