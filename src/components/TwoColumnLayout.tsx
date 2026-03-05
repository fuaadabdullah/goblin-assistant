// Stub implementation for TwoColumnLayout

import React from 'react';

interface TwoColumnLayoutProps {
  children: React.ReactNode;
  sidebar?: React.ReactNode;
}

export default function TwoColumnLayout({ children, sidebar }: TwoColumnLayoutProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <div className="lg:col-span-1">
        {sidebar}
      </div>
      <div className="lg:col-span-3">
        {children}
      </div>
    </div>
  );
}
