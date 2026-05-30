import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { MessageSquare, Search, Settings, LogOut, Home, X, Menu } from 'lucide-react';
import Logo from './Logo';
import MobileDrawer from './MobileDrawer';
import { useUIStore } from '../store/uiStore';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const router = useRouter();
  const setMobileNavOpen = useUIStore((s) => s.setMobileNavOpen);
  const isMobileMenuOpen = useUIStore((s) => s.mobileNavOpen);

  const handleLogout = () => {
    // Clear any stored tokens
    localStorage.removeItem('token');
    // Navigate to login page
    router.push('/login');
  };

  React.useEffect(() => {
    // Close mobile nav on route changes
    setMobileNavOpen(false);
  }, [router.asPath, setMobileNavOpen]);

  const isActive = (path: string) => router.pathname === path;

  const navItems = [
    { path: '/', icon: Home, label: 'Home' },
    { path: '/chat', icon: MessageSquare, label: 'Chat' },
    { path: '/search', icon: Search, label: 'Search' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <header className="bg-surface/90 backdrop-blur shadow-sm border-b border-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo and Title */}
            <div className="flex items-center space-x-4">
              <Link
                href="/"
                className="flex items-center space-x-3 hover:opacity-80 transition-opacity"
              >
                <Logo
                  size="sm"
                  variant="simple"
                  animated={false}
                  decorative
                  ariaLabel="Goblin Assistant"
                />
                <h1 className="text-xl font-bold text-text hidden sm:block">Goblin Assistant</h1>
              </Link>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                return (
                  <Link
                    key={item.path}
                    href={item.path}
                    className={`flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                      isActive(item.path)
                        ? 'text-primary bg-primary/10 border border-primary/30'
                        : 'text-muted hover:text-text hover:bg-surface-hover'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </Link>
                );
              })}

              {/* Logout Button */}
              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 px-3 py-2 rounded-md text-sm font-medium text-danger hover:brightness-110 hover:bg-danger/10 transition-colors ml-4"
              >
                <LogOut className="h-4 w-4" />
                <span>Logout</span>
              </button>
            </nav>

            {/* Mobile menu button */}
            <div className="md:hidden">
              <button
                onClick={() => setMobileNavOpen(!isMobileMenuOpen)}
                className="p-2 rounded-md text-muted hover:text-text hover:bg-surface-hover"
                aria-label={isMobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              >
                {isMobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation rendered via MobileDrawer */}
        <MobileDrawer title="Menu" ariaLabel="Primary mobile navigation">
          <div className="px-2 pt-2 pb-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  href={item.path}
                  onClick={() => setMobileNavOpen(false)}
                  className={`flex items-center space-x-3 px-3 py-2 rounded-md text-base font-medium transition-colors ${
                    isActive(item.path)
                      ? 'text-primary bg-primary/10 border border-primary/30'
                      : 'text-muted hover:text-text hover:bg-surface-hover'
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}

            {/* Mobile Logout Button */}
            <button
              onClick={() => {
                handleLogout();
                setMobileNavOpen(false);
              }}
              className="flex items-center space-x-3 px-3 py-2 rounded-md text-base font-medium text-danger hover:brightness-110 hover:bg-danger/10 transition-colors w-full text-left"
            >
              <LogOut className="h-5 w-5" />
              <span>Logout</span>
            </button>
          </div>
        </MobileDrawer>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">{children}</main>
    </div>
  );
};

export default Layout;
