import { ReactNode } from 'react';

interface TwoColumnLayoutProps {
  sidebar: ReactNode;
  children: ReactNode;
  sidebarWidth?: 'narrow' | 'normal' | 'wide';
  mainId?: string;
  mainLabel?: string;
}

/**
 * Two-column layout: left sidebar (navigation + controls), right main content
 */
const TwoColumnLayout = ({
  sidebar,
  children,
  sidebarWidth = 'normal',
  mainId = 'main-content',
  mainLabel,
}: TwoColumnLayoutProps) => {
  const widthClasses = {
    narrow: 'w-48',
    normal: 'w-64',
    wide: 'w-80',
  };

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {' '}
      {/* Subtract header height */}
      {/* Left Sidebar */}
      <aside
        className={`${widthClasses[sidebarWidth]} bg-surface border-r border-border overflow-y-auto flex-shrink-0`}
      >
        <div className="p-4">{sidebar}</div>
      </aside>
      {/* Main Content */}
      <main
        className="flex-1 overflow-y-auto bg-bg"
        id={mainId}
        tabIndex={-1}
        aria-label={mainLabel}
      >
        <div className="p-6">{children}</div>
      </main>
    </div>
  );
};

export default TwoColumnLayout;
