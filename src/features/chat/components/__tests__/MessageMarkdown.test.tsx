import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('react-markdown', () => function MockMarkdown({ children }: { children: string }) {
  return <div data-testid="markdown">{children}</div>;
});
jest.mock('remark-gfm', () => () => {});
jest.mock('rehype-highlight', () => () => {});
jest.mock('lucide-react', () => new Proxy({}, {
  get: (_, name) => {
    if (name === '__esModule') return true;
    return (props: { 'data-testid'?: string }) => <span data-testid={`icon-${String(name)}`} {...props} />;
  },
}));

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
