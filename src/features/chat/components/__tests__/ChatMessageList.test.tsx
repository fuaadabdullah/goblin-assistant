import { createRef } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import ChatMessageList from '../ChatMessageList';

jest.mock('../StreamingMessage', () => ({
  __esModule: true,
  default: ({ message }: { message: { content: string } }) => <span>{message.content}</span>,
}));

jest.mock('../MessageTimestamp', () => ({
  __esModule: true,
  default: ({ createdAt }: { createdAt: string }) => <time>{createdAt}</time>,
}));

jest.mock('../MessageActions', () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock('../ChatEmptyState', () => ({
  __esModule: true,
  default: () => <div>Empty state</div>,
}));

const baseProps = {
  quickPrompts: [],
  onPromptClick: jest.fn(),
  bottomRef: createRef<HTMLDivElement>(),
  isSending: false,
};

const messages = [
  {
    id: 'msg-1',
    createdAt: '2026-03-09T10:00:00.000Z',
    role: 'user' as const,
    content: 'Alpha',
  },
  {
    id: 'msg-2',
    createdAt: '2026-03-09T10:01:00.000Z',
    role: 'assistant' as const,
    content: 'Beta',
  },
  {
    id: 'msg-3',
    createdAt: '2026-03-09T10:02:00.000Z',
    role: 'assistant' as const,
    content: 'Gamma',
  },
];

describe('ChatMessageList', () => {
  it('preserves DOM identity for messages across reorder and delete operations', () => {
    const { rerender } = render(
      <ChatMessageList
        {...baseProps}
        messages={messages}
      />
    );

    const alphaNode = screen.getByText('Alpha').closest('li');
    const betaNode = screen.getByText('Beta').closest('li');
    const gammaNode = screen.getByText('Gamma').closest('li');

    expect(alphaNode).not.toBeNull();
    expect(betaNode).not.toBeNull();
    expect(gammaNode).not.toBeNull();

    rerender(
      <ChatMessageList
        {...baseProps}
        messages={[messages[2], messages[0], messages[1]]}
      />
    );

    const reorderedItems = screen.getAllByRole('listitem');
    expect(reorderedItems[0]).toBe(gammaNode);
    expect(reorderedItems[1]).toBe(alphaNode);
    expect(reorderedItems[2]).toBe(betaNode);

    rerender(
      <ChatMessageList
        {...baseProps}
        messages={[messages[2], messages[1]]}
      />
    );

    const remainingItems = screen.getAllByRole('listitem');
    expect(remainingItems[0]).toBe(gammaNode);
    expect(remainingItems[1]).toBe(betaNode);
    expect(screen.queryByText('Alpha')).not.toBeInTheDocument();
  });

  it('formats message metadata cost with per-message precision', () => {
    render(
      <ChatMessageList
        {...baseProps}
        messages={[
          {
            id: 'msg-cost',
            createdAt: '2026-03-09T10:03:00.000Z',
            role: 'assistant',
            content: 'Costed response',
            meta: {
              cost_usd: 0.01234,
              usage: { total_tokens: 42 },
              model: 'gpt-4o-mini',
              provider: 'openai',
            },
          },
        ]}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Details' }));
    expect(screen.getByText('$0.0123')).toBeInTheDocument();
  });
});
