import type { ComponentType, ReactNode } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';

interface PageTransitionProps {
  routeKey: string;
  children: ReactNode;
}

const MotionDiv = motion.div as ComponentType<Record<string, unknown>>;

export default function PageTransition({ routeKey, children }: PageTransitionProps) {
  const reduceMotion = useReducedMotion();

  return (
    <AnimatePresence mode="wait" initial={false}>
      <MotionDiv
        key={routeKey}
        initial={reduceMotion ? { opacity: 1 } : { opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={reduceMotion ? { opacity: 1 } : { opacity: 0, y: -4 }}
        transition={{ duration: reduceMotion ? 0 : 0.16, ease: 'easeOut' }}
      >
        {children}
      </MotionDiv>
    </AnimatePresence>
  );
}
