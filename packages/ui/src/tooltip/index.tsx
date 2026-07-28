import * as React from 'react';
import * as TooltipPrimitive from '@radix-ui/react-tooltip';
import { cn } from '../utils';

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactNode;
  position?: 'top' | 'bottom' | 'left' | 'right';
  delay?: number;
}

const sideMap = {
  top: 'top',
  bottom: 'bottom',
  left: 'left',
  right: 'right',
} as const;

/**
 * Tooltip — Radix-backed tooltip with portal rendering and collision handling.
 *
 * Preserves the legacy props API (`content`, `position`, `delay`) so existing
 * call sites (StatusCard, stories, DesignSystemFoundation) need no changes.
 * `position` maps to Radix `side`; `delay` maps to `delayDuration` (ms).
 */
const Tooltip = React.forwardRef<HTMLButtonElement, TooltipProps>(
  ({ content, children, position = 'top', delay = 300 }, _ref) => (
    <TooltipPrimitive.Provider delayDuration={delay} skipDelayDuration={300}>
      <TooltipPrimitive.Root>
        <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content
            side={sideMap[position]}
            sideOffset={6}
            align="center"
            collisionPadding={8}
            className={cn(
              'goblin-motion-presence z-50 max-w-xs rounded-md border border-border bg-surface px-3 py-2 text-xs font-medium text-text shadow-lg',
              'whitespace-normal break-words pointer-events-none',
              'data-[state=delayed-open]:animate-in data-[state=delayed-open]:fade-in-0',
              'data-[state=instant-open]:animate-in data-[state=instant-open]:fade-in-0',
              'data-[state=closed]:animate-out data-[state=closed]:fade-out-0',
              'data-[side=top]:animate-in data-[side=top]:slide-in-from-bottom-1',
              'data-[side=bottom]:animate-in data-[side=bottom]:slide-in-from-top-1',
              'data-[side=left]:animate-in data-[side=left]:slide-in-from-right-1',
              'data-[side=right]:animate-in data-[side=right]:slide-in-from-left-1'
            )}
          >
            {content}
            <TooltipPrimitive.Arrow
              className="fill-surface border border-border"
              width={10}
              height={6}
            />
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  )
);

Tooltip.displayName = 'Tooltip';

export { Tooltip };
export default Tooltip;
