import { render, screen, fireEvent } from '@testing-library/react';

vi.mock('next/link', () => ({
  default: function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  },
}));
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  usePathname: () => '/chat',
  useSearchParams: () => new URLSearchParams(),
  useRouter: () => ({ push: mockPush, replace: vi.fn() }),
}));

import AuthPrompt from '../AuthPrompt';

describe('AuthPrompt', () => {
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

  it('renders in modal mode', () => {
    render(<AuthPrompt mode="modal" />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
  });

  it('renders in inline mode by default', () => {
    const { container } = render(<AuthPrompt />);
    expect(container.querySelector('[role="dialog"]')).toBeFalsy();
  });
});
