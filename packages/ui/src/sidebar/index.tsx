import * as React from 'react';
import { cn } from '../utils';

export interface SidebarProps extends React.HTMLAttributes<HTMLElement> {
  collapsed?: boolean;
}

export const Sidebar = React.forwardRef<HTMLElement, SidebarProps>(
  ({ collapsed = false, className, ...props }, ref) => (
    <aside
      ref={ref}
      data-collapsed={collapsed ? 'true' : 'false'}
      className={cn(
        'goblin-motion-width flex h-full min-h-0 flex-col border-r border-border bg-surface text-text',
        collapsed ? 'w-16' : 'w-72',
        className
      )}
      {...props}
    />
  )
);
Sidebar.displayName = 'Sidebar';

export const SidebarHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      ref={ref}
      className={cn('flex min-h-14 items-center gap-3 border-b border-divider px-4', className)}
      {...props}
    />
  )
);
SidebarHeader.displayName = 'SidebarHeader';

export const SidebarContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn('min-h-0 flex-1 overflow-y-auto p-3', className)} {...props} />
));
SidebarContent.displayName = 'SidebarContent';

export const SidebarFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('border-t border-divider p-3', className)} {...props} />
  )
);
SidebarFooter.displayName = 'SidebarFooter';

export interface SidebarItemProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
  icon?: React.ReactNode;
}

export const SidebarItem = React.forwardRef<HTMLButtonElement, SidebarItemProps>(
  ({ active = false, icon, className, children, type = 'button', ...props }, ref) => (
    <button
      ref={ref}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'goblin-focus-ring goblin-motion-colors flex min-h-10 w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm font-medium text-muted hover:bg-surface-hover hover:text-text',
        active && 'bg-primary/15 text-primary',
        className
      )}
      type={type}
      {...props}
    >
      {icon && (
        <span aria-hidden="true" className="flex h-5 w-5 shrink-0 items-center justify-center">
          {icon}
        </span>
      )}
      <span className="min-w-0 truncate">{children}</span>
    </button>
  )
);
SidebarItem.displayName = 'SidebarItem';

export const SidebarGroup = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} role="group" className={cn('flex flex-col gap-1', className)} {...props} />
  )
);
SidebarGroup.displayName = 'SidebarGroup';

export interface SidebarGroupLabelProps extends React.HTMLAttributes<HTMLHeadingElement> {
  as?: 'h2' | 'h3' | 'h4' | 'div';
}

export const SidebarGroupLabel = React.forwardRef<HTMLHeadingElement, SidebarGroupLabelProps>(
  ({ as: Tag = 'h3', className, ...props }, ref) => (
    <Tag
      ref={ref as React.Ref<HTMLHeadingElement>}
      className={cn(
        'px-3 pt-3 pb-1 text-xs font-semibold uppercase tracking-wide text-text-muted',
        className
      )}
      {...props}
    />
  )
);
SidebarGroupLabel.displayName = 'SidebarGroupLabel';

export const SidebarSeparator = React.forwardRef<
  HTMLHRElement,
  React.HTMLAttributes<HTMLHRElement>
>(({ className, ...props }, ref) => (
  <hr
    ref={ref}
    role="separator"
    className={cn('my-2 border-0 border-t border-divider', className)}
    {...props}
  />
));
SidebarSeparator.displayName = 'SidebarSeparator';
