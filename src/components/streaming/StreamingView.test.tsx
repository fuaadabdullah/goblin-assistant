import { render, waitFor } from '@testing-library/react';
import StreamingView from './StreamingView';

describe('StreamingView', () => {
  it('renders appended token chunks with deterministic chunk indices', async () => {
    const { container, rerender } = render(
      <StreamingView streamingText="Hello" isStreaming={true} />
    );

    await waitFor(() => {
      expect(container.querySelector('[data-token-index="5"]')).toHaveTextContent('Hello');
    });

    const firstTokenNode = container.querySelector('[data-token-index="5"]');

    rerender(<StreamingView streamingText="Hello world" isStreaming={true} />);

    await waitFor(() => {
      expect(container.querySelector('[data-token-index="11"]')).toHaveTextContent('world');
    });

    expect(container.querySelector('[data-token-index="5"]')).toBe(firstTokenNode);
  });
});
