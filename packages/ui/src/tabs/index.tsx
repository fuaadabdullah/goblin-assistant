import * as React from 'react';
import { cn } from '../utils';

type TabsContextValue = {
  value: string;
  setValue: (value: string) => void;
  baseId: string;
};

const TabsContext = React.createContext<TabsContextValue | null>(null);

function useTabsContext(component: string) {
  const context = React.useContext(TabsContext);
  if (!context) {
    throw new Error(`${component} must be used inside Tabs`);
  }
  return context;
}

export interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  value?: string;
}

export function Tabs({
  value,
  defaultValue,
  onValueChange,
  className,
  children,
  ...props
}: TabsProps) {
  const reactId = React.useId();
  const [internalValue, setInternalValue] = React.useState(defaultValue ?? '');
  const selectedValue = value ?? internalValue;

  const setValue = React.useCallback(
    (nextValue: string) => {
      if (value === undefined) {
        setInternalValue(nextValue);
      }
      onValueChange?.(nextValue);
    },
    [onValueChange, value]
  );

  return (
    <TabsContext.Provider value={{ value: selectedValue, setValue, baseId: reactId }}>
      <div className={cn('space-y-4', className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

export interface TabsListProps extends React.HTMLAttributes<HTMLDivElement> {}

export function TabsList({ className, ...props }: TabsListProps) {
  return (
    <div
      role="tablist"
      className={cn(
        'inline-flex rounded-md border border-border bg-surface p-1 shadow-sm',
        className
      )}
      {...props}
    />
  );
}

export interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

export const TabsTrigger = React.forwardRef<HTMLButtonElement, TabsTriggerProps>(
  ({ value, className, type = 'button', ...props }, ref) => {
    const context = useTabsContext('TabsTrigger');
    const selected = context.value === value;

    const moveFocus = (event: React.KeyboardEvent<HTMLButtonElement>) => {
      const tablist = event.currentTarget.closest('[role="tablist"]');
      if (!tablist) return;

      const tabs = Array.from(
        tablist.querySelectorAll<HTMLButtonElement>('[role="tab"]:not(:disabled)')
      );
      const currentIndex = tabs.indexOf(event.currentTarget);
      if (currentIndex < 0) return;

      const lastIndex = tabs.length - 1;
      const nextIndex =
        event.key === 'ArrowRight' || event.key === 'ArrowDown'
          ? currentIndex === lastIndex
            ? 0
            : currentIndex + 1
          : event.key === 'ArrowLeft' || event.key === 'ArrowUp'
            ? currentIndex === 0
              ? lastIndex
              : currentIndex - 1
            : event.key === 'Home'
              ? 0
              : event.key === 'End'
                ? lastIndex
                : currentIndex;

      if (nextIndex !== currentIndex) {
        event.preventDefault();
        tabs[nextIndex]?.focus();
        tabs[nextIndex]?.click();
      }
    };

    return (
      <button
        ref={ref}
        id={`${context.baseId}-trigger-${value}`}
        aria-controls={`${context.baseId}-panel-${value}`}
        aria-selected={selected}
        className={cn(
          'goblin-focus-ring goblin-motion-colors inline-flex min-h-10 items-center justify-center rounded-sm px-3 py-2 text-sm font-medium text-muted disabled:pointer-events-none disabled:opacity-50',
          selected ? 'bg-primary text-bg shadow-sm' : 'hover:bg-surface-hover hover:text-text',
          className
        )}
        role="tab"
        tabIndex={selected ? 0 : -1}
        type={type}
        onKeyDown={(event) => {
          props.onKeyDown?.(event);
          if (!event.defaultPrevented) {
            moveFocus(event);
          }
        }}
        onClick={(event) => {
          props.onClick?.(event);
          if (!event.defaultPrevented) {
            context.setValue(value);
          }
        }}
        {...props}
      />
    );
  }
);
TabsTrigger.displayName = 'TabsTrigger';

export interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

export const TabsContent = React.forwardRef<HTMLDivElement, TabsContentProps>(
  ({ value, className, ...props }, ref) => {
    const context = useTabsContext('TabsContent');
    const selected = context.value === value;
    return (
      <div
        ref={ref}
        id={`${context.baseId}-panel-${value}`}
        aria-labelledby={`${context.baseId}-trigger-${value}`}
        hidden={!selected}
        role="tabpanel"
        tabIndex={0}
        className={cn('goblin-focus-ring', className)}
        {...props}
      />
    );
  }
);
TabsContent.displayName = 'TabsContent';
