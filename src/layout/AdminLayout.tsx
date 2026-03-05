import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { useRouter } from 'next/router';
import Navigation from '../components/Navigation';
import Seo from '../components/Seo';
import { initDatadog } from '../utils/datadog-rum';
import { useAuthStore } from '../store/authStore';

interface AdminLayoutProps {
  children: ReactNode;
  fullWidth?: boolean;
  mainId?: string;
  mainLabel?: string;
}

export default function AdminLayout({
  children,
  fullWidth = false,
  mainId,
  mainLabel = 'Admin',
}: AdminLayoutProps) {
  const router = useRouter();
  const { isAuthenticated, isHydrated, hasRole } = useAuthStore();
  const contentClassName = fullWidth ? 'px-6' : 'max-w-7xl mx-auto p-6';

  useEffect(() => {
    // Initialize DataDog RUM and Logs for admin pages only
    initDatadog().catch((error) => {
      console.warn('Failed to initialize DataDog on admin page:', error);
    });
  }, []);

  // Auth guard: redirect non-admin users before rendering anything
  useEffect(() => {
    if (!isHydrated) return; // wait for Zustand store to rehydrate from session
    if (!isAuthenticated || !hasRole('admin')) {
      const redirect = encodeURIComponent(router.asPath);
      void router.replace(`/login?redirect=${redirect}`);
    }
  }, [isHydrated, isAuthenticated, hasRole, router]);

  // Render nothing until hydration is complete and auth is confirmed
  if (!isHydrated || !isAuthenticated || !hasRole('admin')) {
    return null;
  }

  return (
    <div className="min-h-screen bg-bg">
      <Seo title="Admin" description="Goblin Assistant admin area." robots="noindex,nofollow" />
      <Navigation showLogout={true} variant="admin" />
      {mainId ? (
        <main className={contentClassName} id={mainId} tabIndex={-1} aria-label={mainLabel}>
          {children}
        </main>
      ) : (
        <div className={contentClassName}>{children}</div>
      )}
    </div>
  );
}

