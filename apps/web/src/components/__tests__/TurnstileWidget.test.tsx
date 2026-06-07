import { render } from '@testing-library/react';
import TurnstileWidget from '../TurnstileWidget';

describe('TurnstileWidget Component', () => {
  beforeEach(() => {
    (window as any).turnstile = {
      render: vi.fn(() => 'mock-widget-id'),
      reset: vi.fn(),
      remove: vi.fn(),
      execute: vi.fn(),
      getResponse: vi.fn(),
    };
  });

  afterEach(() => {
    delete (window as any).turnstile;
  });

  it('should render a container div', () => {
    const { container } = render(<TurnstileWidget siteKey="test-site-key" onVerify={vi.fn()} />);
    expect(container.querySelector('.turnstile-widget')).toBeInTheDocument();
  });

  it('should render invisible mode with hidden div', () => {
    const { container } = render(
      <TurnstileWidget siteKey="test-site-key" onVerify={vi.fn()} mode="invisible" />
    );
    const div = container.firstChild as HTMLElement;
    expect(div.style.display).toBe('none');
  });

  it('should clean up widget on unmount', () => {
    const { unmount } = render(<TurnstileWidget siteKey="test-site-key" onVerify={vi.fn()} />);
    unmount();
  });

  it('should accept theme and size props', () => {
    const { container } = render(
      <TurnstileWidget siteKey="test-key" onVerify={vi.fn()} theme="dark" size="compact" />
    );
    expect(container.querySelector('.turnstile-widget')).toBeInTheDocument();
  });
});
