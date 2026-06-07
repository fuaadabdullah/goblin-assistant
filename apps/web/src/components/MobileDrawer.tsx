import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { useUIStore } from '../store/uiStore';
import Logo from './Logo';

const MobileDrawer: React.FC<{
  title?: string;
  ariaLabel?: string;
  children?: React.ReactNode;
}> = ({ title = 'Menu', ariaLabel = 'Mobile navigation', children }) => {
  const isOpen = useUIStore((s) => s.mobileNavOpen);
  const close = useUIStore((s) => s.setMobileNavOpen);
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        close(false);
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen, close]);

  useEffect(() => {
    if (isOpen) {
      // focus the panel for keyboard users
      setTimeout(() => panelRef.current?.focus(), 50);
      // prevent body scroll
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
  }, [isOpen]);

  return (
    <>
      {isOpen && (
        <>
          {/* Overlay */}
          <div
            onClick={() => close(false)}
            className="fixed inset-0 bg-black/40 z-40"
            aria-hidden="true"
          />

          {/* Drawer panel */}
          <div
            className="fixed top-0 left-0 bottom-0 w-72 z-50 bg-surface border-r border-border shadow-lg overflow-auto"
            role="dialog"
            aria-label={ariaLabel}
          >
            <div ref={panelRef} tabIndex={-1} className="h-full flex flex-col">
              <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                <div className="flex items-center space-x-3">
                  <Logo
                    size="sm"
                    variant="simple"
                    animated={false}
                    decorative
                    ariaLabel="Goblin Assistant"
                  />
                  <span className="font-semibold text-lg text-primary">{title}</span>
                </div>
                <button
                  type="button"
                  className="p-2 rounded-md text-muted hover:text-text"
                  onClick={() => close(false)}
                  aria-label="Close menu"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-4 flex-1">{children}</div>

              <div className="p-4 border-t border-border">
                <p className="text-sm text-muted">Made with 💚 — Goblin Assistant</p>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};

export default MobileDrawer;
