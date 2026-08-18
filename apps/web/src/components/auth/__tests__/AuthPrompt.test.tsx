import { render, screen, fireEvent } from '@testing-library/react';

const navigationState = vi.hoisted(() => ({
  pathname: '/chat' as string | null,
  searchParams: new URLSearchParams(),
}));

vi.mock('next/link', () => ({
  default: function MockLink({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string | { pathname: string; query?: Record<string, string> };
  }) {
    const resolvedHref =
      typeof href === 'string'
        ? href
        : `${href.pathname}${
            href.query && Object.keys(href.query).length > 0
              ? `?${new URLSearchParams(href.query).toString()}`
              : ''
          }`;
    return <a href={resolvedHref}>{children}</a>;
  },
}));
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  usePathname: () => navigationState.pathname,
  useSearchParams: () => navigationState.searchParams,
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
}));

import AuthPrompt from '../AuthPrompt';

describe('AuthPrompt', () => {
  beforeEach(() => {
    navigationState.pathname = '/chat';
    navigationState.searchParams = new URLSearchParams();
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
      callback(0);
      return 1;
    });
    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders default title and message', () => {
    render(<AuthPrompt />);
    expect(screen.getByText(/sign in required/i)).toBeInTheDocument();
  });

  it('renders custom title', () => {
    render(<AuthPrompt title="Custom Title" />);
    expect(screen.getByText('Custom Title')).toBeInTheDocument();
  });

  it('renders sign in and create account links', () => {
    render(<AuthPrompt />);
    expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /create account/i })).toBeInTheDocument();
  });

  it('renders guest button when allowGuest is true', () => {
    render(<AuthPrompt allowGuest />);
    expect(screen.getByText(/guest/i)).toBeInTheDocument();
  });

  it('renders close button when onClose provided', () => {
    const onClose = vi.fn();
    render(<AuthPrompt onClose={onClose} />);
    const closeBtn =
      screen.queryByLabelText(/close/i) ||
      screen.queryByRole('button', { name: /close|dismiss|×/i });
    if (closeBtn) {
      fireEvent.click(closeBtn);
      expect(onClose).toHaveBeenCalled();
    }
  });

  it('builds links from the current pathname and query string', () => {
    navigationState.pathname = '/chat';
    navigationState.searchParams = new URLSearchParams('tab=security&step=2');

    render(<AuthPrompt />);

    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute(
      'href',
      '/login?from=%2Fchat%3Ftab%3Dsecurity%26step%3D2'
    );
    expect(screen.getByRole('link', { name: /create account/i })).toHaveAttribute(
      'href',
      '/login?mode=register&from=%2Fchat%3Ftab%3Dsecurity%26step%3D2'
    );
  });

  it('falls back to the root route when pathname is unavailable', () => {
    navigationState.pathname = null;
    navigationState.searchParams = new URLSearchParams('tab=security');

    render(<AuthPrompt />);

    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute(
      'href',
      '/login?from=%2F'
    );
    expect(screen.getByRole('link', { name: /create account/i })).toHaveAttribute(
      'href',
      '/login?mode=register&from=%2F'
    );
  });

  it('renders in modal mode', () => {
    render(<AuthPrompt mode="modal" />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
  });

  it('renders in inline mode by default', () => {
    const { container } = render(<AuthPrompt />);
    expect(container.querySelector('[role="dialog"]')).toBeFalsy();
  });

  it('traps focus in modal mode and closes on Escape', () => {
    const onClose = vi.fn();
    const previous = document.createElement('button');
    previous.textContent = 'previous';
    document.body.appendChild(previous);
    previous.focus();

    const { unmount } = render(<AuthPrompt mode="modal" onClose={onClose} allowGuest />);

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /close/i })).toHaveFocus();

    const links = screen.getAllByRole('link');
    links[links.length - 1]!.focus();

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Tab' });
    expect(screen.getByRole('button', { name: /close/i })).toHaveFocus();

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(onClose).toHaveBeenCalledTimes(1);

    unmount();
    expect(previous).toHaveFocus();
    previous.remove();
  });

  it('wraps focus backward with Shift+Tab in modal mode', () => {
    const onClose = vi.fn();

    render(<AuthPrompt mode="modal" onClose={onClose} allowGuest />);

    const dialog = screen.getByRole('dialog');
    const closeButton = screen.getByRole('button', { name: /close/i });
    expect(closeButton).toHaveFocus();

    fireEvent.keyDown(dialog, { key: 'Tab', shiftKey: true });

    expect(screen.getByRole('link', { name: /continue as guest/i })).toHaveFocus();
  });

  it('ignores non-Tab keys in modal mode', () => {
    const onClose = vi.fn();

    render(<AuthPrompt mode="modal" onClose={onClose} />);

    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'ArrowDown' });

    expect(onClose).not.toHaveBeenCalled();
  });
});
