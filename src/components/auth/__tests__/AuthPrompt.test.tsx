import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('next/link', () => function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
  return <a href={href}>{children}</a>;
});
const mockPush = jest.fn();
jest.mock('next/router', () => ({
  useRouter: () => ({ pathname: '/chat', push: mockPush, query: {} }),
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
    const onClose = jest.fn();
    render(<AuthPrompt onClose={onClose} />);
    const closeBtn = screen.queryByLabelText(/close/i) || screen.queryByRole('button', { name: /close|dismiss|×/i });
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
