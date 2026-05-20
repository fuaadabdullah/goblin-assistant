import React, { useEffect, useRef } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { X } from 'lucide-react';
import { useUIStore } from '../store/uiStore';
import Logo from './Logo';

const overlayVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

const panelVariants = {
  hidden: { x: '-100%' },
  visible: { x: 0 },
};

const MobileDrawer: React.FC<{ title?: string; ariaLabel?: string; children?: React.ReactNode }> = ({ title = 'Menu', ariaLabel = 'Mobile navigation', children }) => {
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

  const shouldReduceMotion = useReducedMotion();

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
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Overlay */}
          <motion.div
            initial={shouldReduceMotion ? 'visible' : 'hidden'}
            animate="visible"
            exit={shouldReduceMotion ? 'visible' : 'hidden'}
            variants={overlayVariants}
            transition={{ duration: shouldReduceMotion ? 0 : 0.18 }}
            onClick={() => close(false)}
            className="fixed inset-0 bg-black/40 z-40"
            aria-hidden="true"
          />

          {/* Drawer panel */}
          <motion.div
            initial={shouldReduceMotion ? 'visible' : 'hidden'}
            animate="visible"
            exit={shouldReduceMotion ? 'visible' : 'hidden'}
            variants={panelVariants}
            transition={{ type: 'tween', duration: shouldReduceMotion ? 0 : 0.22 }}
            className="fixed top-0 left-0 bottom-0 w-72 z-50 bg-surface border-r border-border shadow-lg overflow-auto"
            role="dialog"
            aria-label={ariaLabel}
          >
            <div ref={panelRef} tabIndex={-1} className="h-full flex flex-col">
                <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                  <div className="flex items-center space-x-3">
                    <Logo size="sm" variant="simple" animated={false} decorative ariaLabel="Goblin Assistant" />
                    <span className="font-semibold text-lg text-primary">{title}</span>
                  </div>
                  <button
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
            </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default MobileDrawer;
