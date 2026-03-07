import Link from 'next/link';
import { useRouter } from 'next/router';
import { Home, MessageSquare, Search, FlaskConical, User, HelpCircle, LayoutDashboard, Puzzle, ScrollText, Settings, Users, LogOut } from 'lucide-react';
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
          {/* Primary Nav */}
          <div className="flex items-center space-x-3">
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
        </div>
      </div>
    </nav>
  );
};

export default Navigation;
