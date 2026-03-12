import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

jest.mock('next/link', () => function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
  return <a href={href}>{children}</a>;
});
const mockPush = jest.fn();
jest.mock('next/router', () => ({
  useRouter: () => ({ pathname: '/', push: mockPush, events: { on: jest.fn(), off: jest.fn() } }),
}));
jest.mock('lucide-react', () => new Proxy({}, {
  get: (_, name) => {
    if (name === '__esModule') return true;
    return (props: Record<string, unknown>) => <span data-testid={`icon-${String(name)}`} {...props} />;
  },
}));
jest.mock('../HealthHeader', () => function MockHealthHeader() { return <div data-testid="health-header" />; });
jest.mock('../ContrastModeToggle', () => function MockToggle() { return <div data-testid="contrast-toggle" />; });
jest.mock('../Logo', () => function MockLogo() { return <div data-testid="logo" />; });
const mockLogout = jest.fn();
jest.mock('../../hooks/api/useAuthSession', () => ({
  useAuthSession: () => ({ logout: mockLogout, isAuthenticated: true }),
}));

import Navigation from '../Navigation';

describe('Navigation', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders logo', () => {
    render(<Navigation />);
    expect(screen.getByTestId('logo')).toBeInTheDocument();
  });

  it('renders nav links', () => {
    render(<Navigation />);
    const chatLinks = screen.getAllByText(/chat/i);
    expect(chatLinks.length).toBeGreaterThanOrEqual(1);
  });

  it('shows logout button when showLogout is true', () => {
    render(<Navigation showLogout />);
    const btns = screen.getAllByRole('button', { name: /logout/i });
    expect(btns.length).toBeGreaterThanOrEqual(1);
  });

  it('renders admin variant with health header', () => {
    render(<Navigation variant="admin" />);
    const headers = screen.getAllByTestId('health-header');
    expect(headers.length).toBeGreaterThanOrEqual(1);
  });

  it('renders contrast mode toggle', () => {
    render(<Navigation />);
    const toggles = screen.getAllByTestId('contrast-toggle');
    expect(toggles.length).toBeGreaterThanOrEqual(1);
  });

  it('toggles mobile menu', () => {
    render(<Navigation />);
    const menuBtn = screen.getByLabelText(/menu/i) || screen.getByRole('button', { name: /menu/i });
    fireEvent.click(menuBtn);
  });
});
