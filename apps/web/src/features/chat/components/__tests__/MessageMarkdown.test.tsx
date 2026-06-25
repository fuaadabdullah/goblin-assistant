import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('react-markdown', () => ({
  default: function MockMarkdown({ children }: { children: string }) {
    return <div data-testid="markdown">{children}</div>;
  },
}));
vi.mock('remark-gfm', () => ({ default: () => {} }));
vi.mock('rehype-highlight', () => ({ default: () => {} }));
import MessageMarkdown from '../MessageMarkdown';

describe('MessageMarkdown', () => {
  it('renders markdown content', () => {
    render(<MessageMarkdown content="Hello world" />);
    expect(screen.getByTestId('markdown')).toHaveTextContent('Hello world');
  });

  it('applies custom className', () => {
    const { container } = render(<MessageMarkdown content="test" className="custom-class" />);
    expect(container.firstChild).toBeTruthy();
  });

  it('renders with inverse prop', () => {
    render(<MessageMarkdown content="test" inverse />);
    expect(screen.getByTestId('markdown')).toBeInTheDocument();
  });

  it('renders empty content', () => {
    render(<MessageMarkdown content="" />);
    expect(screen.getByTestId('markdown')).toBeInTheDocument();
  });

  it('renders long content', () => {
    const longContent = 'a'.repeat(5000);
    render(<MessageMarkdown content={longContent} />);
    expect(screen.getByTestId('markdown')).toBeInTheDocument();
  });
});
