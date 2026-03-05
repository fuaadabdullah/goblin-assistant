import * as React from 'react';
import { clsx } from 'clsx';
import { Header } from './Header';

interface MainLayoutProps {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function MainLayout({ 
  children, 
  title, 
  subtitle, 
  actions, 
  className 
}: MainLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <Header title={title} subtitle={subtitle} actions={actions} />
      
      <main className={clsx('container mx-auto px-4 sm:px-6 lg:px-8 py-6', className)}>
        {children}
      </main>
    </div>
  );
}
