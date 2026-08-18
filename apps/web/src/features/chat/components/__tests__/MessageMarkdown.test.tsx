import { act, fireEvent, render, screen } from '@testing-library/react';

const clipboardWriteText = vi.fn().mockResolvedValue(undefined);

vi.mock('react-markdown', () => ({
  default: function MockMarkdown({
    children,
    components,
  }: {
    children: string;
    components: Record<string, (...args: Array<any>) => any>;
  }) {
    const inlineCode = components.code({
      className: '',
      children: 'inline sample',
    } as never);
    const languageCode = components.code({
      className: 'language-ts',
      children: 'const answer = 42;',
    } as never);
    const hashLink = components.a({
      href: '#anchor',
      children: 'hash link',
    } as never);
    const externalLink = components.a({
      href: 'https://example.com',
      children: 'external link',
    } as never);
    const table = components.table({
      children: (
        <tbody>
          <tr>
            {components.th({ children: 'Name' } as never)}
            {components.td({ children: 'Value' } as never)}
          </tr>
        </tbody>
      ),
    } as never);
    const preBlock = components.pre({
      children: <code className="language-ts">const answer = 42;</code>,
    } as never);

    return (
      <div data-testid="markdown">
        {inlineCode}
        {languageCode}
        {hashLink}
        {externalLink}
        {table}
        {preBlock}
        <p>{children}</p>
      </div>
    );
  },
}));

vi.mock('remark-gfm', () => ({ default: () => {} }));
vi.mock('rehype-highlight', () => ({ default: () => {} }));

import MessageMarkdown from '../MessageMarkdown';

describe('MessageMarkdown', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    clipboardWriteText.mockClear();
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: clipboardWriteText,
      },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders inline code, links, tables, and code fences', () => {
    render(<MessageMarkdown content="Hello world" />);

    expect(screen.getByTestId('markdown')).toHaveTextContent('Hello world');
    expect(screen.getByText('inline sample')).toHaveClass('bg-surface-hover');
    expect(screen.getByText('TypeScript')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'hash link' })).not.toHaveAttribute('target');
    expect(screen.getByRole('link', { name: 'external link' })).toHaveAttribute('target', '_blank');
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('Value')).toBeInTheDocument();
  });

  it('copies the code block text and resets the copied state', async () => {
    render(<MessageMarkdown content="Hello world" inverse />);

    const copyButton = screen.getByRole('button', { name: 'Copy code' });
    await act(async () => {
      fireEvent.click(copyButton);
      await Promise.resolve();
    });

    expect(clipboardWriteText).toHaveBeenCalledWith('const answer = 42;');
    expect(screen.getByRole('button', { name: 'Copied' })).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    expect(screen.getByRole('button', { name: 'Copy code' })).toBeInTheDocument();
    expect(screen.getByText('inline sample')).toHaveClass('text-text-inverse');
  });
});
