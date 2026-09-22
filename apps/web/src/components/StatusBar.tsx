'use client';

import React from 'react';
import { usePathname } from 'next/navigation';
import HealthHeader from './HealthHeader';

const StatusBar: React.FC = () => {
  const pathname = usePathname();

  // On /chat the composer owns the bottom edge of the screen — this fixed bar
  // would cover it. Its health readout also duplicates ChatHeader's
  // ConnectionStatus, which is already visible on that page.
  if (pathname === '/chat') return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-surface/70 backdrop-blur-sm border-t border-border px-2 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
      <div className="max-w-6xl mx-auto flex items-center justify-between text-xs text-muted">
        <div className="flex items-center gap-3">
          <span className="font-mono">GoblinOS</span>
          <span className="hidden sm:inline">•</span>
          <span className="hidden sm:inline">Stable UI</span>
        </div>
        <div className="flex items-center">
          <HealthHeader compact />
        </div>
      </div>
    </div>
  );
};

export default StatusBar;
