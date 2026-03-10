import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import { Home, MessageSquare, Search, FlaskConical, User, HelpCircle, LayoutDashboard, Puzzle, ScrollText, Settings, Users, LogOut, Menu, X } from 'lucide-react';
import HealthHeader from './HealthHeader';
import ContrastModeToggle from './ContrastModeToggle';
import Logo from './Logo';
import { useAuthSession } from '../hooks/api/useAuthSession';

interface NavigationProps {
  onLogout?: () => void | Promise<void>;
  showLogout?: boolean;
  variant?: 'admin' | 'customer';
}

const Navigation = ({ onLogout, showLogout = false, variant = 'customer' }: NavigationProps) => {
  const router = useRouter();
  const { logout } = useAuthSession();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    if (onLogout) {
      await onLogout();
    }
    await router.push('/login');
  };

  const customerItems = [
    { path: '/', label: 'Home', Icon: Home },
    { path: '/chat', label: 'Chat', Icon: MessageSquare },
    { path: '/search', label: 'Search', Icon: Search },
    { path: '/sandbox', label: 'Sandbox', Icon: FlaskConical },
    { path: '/account', label: 'Account', Icon: User },
    { path: '/help', label: 'Help', Icon: HelpCircle },
  ];

  const adminItems = [
    { path: '/admin', label: 'Dashboard', Icon: LayoutDashboard },
    { path: '/admin/providers', label: 'Providers', Icon: Puzzle },
    { path: '/admin/logs', label: 'Logs', Icon: ScrollText },
    { path: '/admin/settings', label: 'Settings', Icon: Settings },
    { path: '/', label: 'Customer View', Icon: Users },
  ];

  const navItems = variant === 'admin' ? adminItems : customerItems;

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [router.asPath]);

  return (
    <nav
      className="bg-surface/90 backdrop-blur border-b border-border shadow-sm sticky top-0 z-40"
      role="navigation"
      aria-label="Primary"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link href="/" className="flex items-center space-x-2">
              <Logo size="sm" variant="simple" animated decorative ariaLabel="Goblin Assistant" />
              <span className="text-lg font-semibold text-primary">Goblin Assistant</span>
            </Link>
            {/* Inline health status pill */}
            {variant === 'admin' && (
              <div className="hidden md:block">
                <HealthHeader compact />
              </div>
            )}
          </div>
          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center space-x-3">
            {navItems.map(item => {
              const isActive = router.pathname === item.path || (item.path !== '/' && router.pathname.startsWith(item.path));
              return (
                <Link
                  key={item.path}
                  href={item.path}
                  className={`flex items-center space-x-2 px-4 py-3 min-h-[44px] text-sm font-medium rounded-lg transition-colors outline-offset-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary ${isActive
                    ? 'text-text bg-surface-active shadow-glow-primary border border-border'
                    : 'text-muted hover:text-text hover:bg-surface-hover'
                    }`}
                  title={item.label}
                >
                  <item.Icon className="w-5 h-5" aria-hidden="true" />
                  <span className="leading-none">{item.label}</span>
                </Link>
              );
            })}
            {/* Utility area: contrast + logout */}
            <div className="flex items-center gap-2 pl-3 ml-3 border-l border-border">
              <div className="hidden sm:flex">
                <ContrastModeToggle />
              </div>
              {showLogout && (
                <button
                  onClick={() => {
                    void handleLogout();
                  }}
                  className="flex items-center space-x-2 px-4 py-3 min-h-[44px] text-sm font-medium text-cta hover:bg-surface-hover rounded-lg transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
                  title="Logout"
                  aria-label="Logout"
                >
                  <LogOut className="w-5 h-5" aria-hidden="true" />
                  <span className="leading-none">Logout</span>
                </button>
              )}
            </div>
          </div>

          {/* Mobile Menu Trigger */}
          <div className="lg:hidden flex items-center gap-2">
            <ContrastModeToggle />
            <button
              type="button"
              onClick={() => setIsMobileMenuOpen((open) => !open)}
              className="inline-flex items-center justify-center rounded-lg border border-border bg-surface-hover p-2 text-text hover:bg-surface-active"
              aria-label={isMobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={isMobileMenuOpen}
              aria-controls="mobile-navigation-panel"
            >
              {isMobileMenuOpen ? <X className="w-5 h-5" aria-hidden="true" /> : <Menu className="w-5 h-5" aria-hidden="true" />}
            </button>
          </div>
        </div>
      </div>

      <div
        id="mobile-navigation-panel"
        className={`lg:hidden border-t border-border bg-surface transition-[max-height,opacity] duration-200 overflow-hidden ${
          isMobileMenuOpen ? 'max-h-[75vh] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-4 py-3 space-y-2">
          {variant === 'admin' ? (
            <div className="rounded-lg border border-border bg-surface-hover p-3">
              <HealthHeader compact />
            </div>
          ) : null}

          {navItems.map(item => {
            const isActive = router.pathname === item.path || (item.path !== '/' && router.pathname.startsWith(item.path));
            return (
              <Link
                key={item.path}
                href={item.path}
                className={`flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium min-h-[44px] ${
                  isActive
                    ? 'text-text bg-surface-active border border-border'
                    : 'text-muted hover:text-text hover:bg-surface-hover'
                }`}
              >
                <item.Icon className="w-5 h-5" aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}

          {showLogout ? (
            <button
              type="button"
              onClick={() => {
                void handleLogout();
              }}
              className="w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium min-h-[44px] text-cta hover:bg-surface-hover"
              aria-label="Logout"
            >
              <LogOut className="w-5 h-5" aria-hidden="true" />
              <span>Logout</span>
            </button>
          ) : null}
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
