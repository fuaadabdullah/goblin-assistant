import type { ReactNode } from 'react';

interface PageTransitionProps {
  routeKey: string;
  children: ReactNode;
}

export default function PageTransition({ routeKey, children }: PageTransitionProps) {
  return (
    <div key={routeKey} className="page-enter">
      {children}
    </div>
  );
}
