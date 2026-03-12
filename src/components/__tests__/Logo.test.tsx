import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import Logo from '../Logo';

// Mock lucide-react Bot icon
jest.mock('lucide-react', () => ({
  Bot: (props: Record<string, unknown>) => <span data-testid="bot-icon" {...props} />,
}));

describe('Logo', () => {
  it('renders full variant by default', () => {
    const { container } = render(<Logo />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('viewBox', '0 0 64 64');
  });

  it('renders simple variant', () => {
    const { container } = render(<Logo variant="simple" />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('viewBox', '0 0 48 48');
  });

  it('renders emoji variant with Bot icon', () => {
    render(<Logo variant="emoji" />);
    expect(screen.getByTestId('bot-icon')).toBeInTheDocument();
  });

  it('applies correct size', () => {
    const { container } = render(<Logo size="xl" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '64');
    expect(svg).toHaveAttribute('height', '64');
  });

  it('applies xs size', () => {
    const { container } = render(<Logo size="xs" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '16');
  });

  it('applies sm size', () => {
    const { container } = render(<Logo size="sm" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '24');
  });

  it('applies lg size', () => {
    const { container } = render(<Logo size="lg" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '48');
  });

  it('renders md size by default', () => {
    const { container } = render(<Logo />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '32');
  });

  it('hides from assistive tech when decorative', () => {
    const { container } = render(<Logo decorative />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('aria-hidden', 'true');
  });

  it('has role=img and aria-label when not decorative', () => {
    const { container } = render(<Logo decorative={false} />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('role', 'img');
    expect(svg).toHaveAttribute('aria-label', 'Goblin Assistant');
  });

  it('includes title element when not decorative', () => {
    render(<Logo decorative={false} />);
    expect(screen.getByText('Goblin Assistant')).toBeInTheDocument();
  });

  it('does not include title when decorative', () => {
    render(<Logo decorative />);
    expect(screen.queryByText('Goblin Assistant')).not.toBeInTheDocument();
  });

  it('uses custom ariaLabel', () => {
    const { container } = render(<Logo ariaLabel="Custom Label" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('aria-label', 'Custom Label');
  });

  it('applies animation class when animated', () => {
    const { container } = render(<Logo animated />);
    const svg = container.querySelector('svg');
    const cls = svg?.getAttribute('class') ?? '';
    expect(cls).toContain('logo-transition');
  });

  it('does not apply animation class when not animated', () => {
    const { container } = render(<Logo animated={false} />);
    const svg = container.querySelector('svg');
    const cls = svg?.getAttribute('class') ?? '';
    expect(cls).not.toContain('logo-transition');
  });

  it('applies custom className', () => {
    const { container } = render(<Logo className="my-class" />);
    const svg = container.querySelector('svg');
    const cls = svg?.getAttribute('class') ?? '';
    expect(cls).toContain('my-class');
  });

  it('emoji variant respects decorative prop', () => {
    const { container } = render(<Logo variant="emoji" decorative />);
    const span = container.firstChild as HTMLElement;
    expect(span).toHaveAttribute('aria-hidden', 'true');
  });

  it('emoji variant has role=img when not decorative', () => {
    const { container } = render(<Logo variant="emoji" decorative={false} />);
    const span = container.firstChild as HTMLElement;
    expect(span).toHaveAttribute('role', 'img');
  });
});
