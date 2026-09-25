'use client';

import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import Navigation from '../components/Navigation';
import Seo from '../components/Seo';
import { useAuthSession } from '../hooks/api/useAuthSession';

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
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { isAuthenticated, isHydrated, isAdmin, isFetching } = useAuthSession();
  const contentClassName = fullWidth ? 'px-6' : 'max-w-7xl mx-auto p-6';

  // Auth guard: redirect non-admin users before rendering anything
  useEffect(() => {
    if (!isHydrated) return; // wait for Zustand store to rehydrate from session
    // The login flows seed this session synchronously and cannot know the
    // admin claim yet, so `isAdmin` is false until the server resolves it.
    // Redirecting on that interim value bounces a real admin straight back
    // to /login; wait for the in-flight validation to land first.
    if (isFetching) return;
    if (!isAuthenticated || !isAdmin) {
      const query = searchParams.toString();
      const asPath = query ? `${pathname}?${query}` : pathname;
      const redirect = encodeURIComponent(asPath ?? '/');
      router.replace(`/login?redirect=${redirect}`);
    }
  }, [isHydrated, isFetching, isAuthenticated, isAdmin, router, pathname, searchParams]);

  // Render nothing until hydration is complete and auth is confirmed
  if (!isHydrated || isFetching || !isAuthenticated || !isAdmin) {
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
