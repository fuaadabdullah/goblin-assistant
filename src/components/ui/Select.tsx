import * as React from 'react';
import * as SelectPrimitive from '@radix-ui/react-select';
import { Check, ChevronDown, ChevronUp } from 'lucide-react';

import { cn } from '@/lib/utils';

const Select = SelectPrimitive.Root;

const SelectGroup = SelectPrimitive.Group;

const SelectValue = SelectPrimitive.Value;

// NOTE: With pnpm + `preserveSymlinks`, TypeScript can fail to "see" common DOM props
// (like `children`/`className`) on Radix primitives due to how their types are composed.
// Runtime is fine; we keep types on the exported wrappers and treat the inner primitives as `any`.
const TriggerPrimitive: any = SelectPrimitive.Trigger;
const IconPrimitive: any = SelectPrimitive.Icon;
const ScrollUpPrimitive: any = SelectPrimitive.ScrollUpButton;
const ScrollDownPrimitive: any = SelectPrimitive.ScrollDownButton;
const ContentPrimitive: any = SelectPrimitive.Content;
const ViewportPrimitive: any = SelectPrimitive.Viewport;
const LabelPrimitive: any = SelectPrimitive.Label;
const ItemPrimitive: any = SelectPrimitive.Item;
const ItemIndicatorPrimitive: any = SelectPrimitive.ItemIndicator;
const ItemTextPrimitive: any = SelectPrimitive.ItemText;
const SeparatorPrimitive: any = SelectPrimitive.Separator;
const PortalPrimitive: any = SelectPrimitive.Portal;

type WithDomStyling = {
  id?: string;
  className?: string;
  children?: React.ReactNode;
};

type SelectTriggerProps = React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger> & WithDomStyling;

const SelectTrigger = React.forwardRef<
  HTMLButtonElement,
  SelectTriggerProps
>(({ className, children, ...props }, ref) => (
  <TriggerPrimitive
    ref={ref}
    className={cn(
      'flex h-11 w-full items-center justify-between rounded-xl border border-border bg-surface px-3 py-2 text-sm text-text data-[placeholder]:text-muted focus:outline-none focus:ring-2 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1',
      className
    )}
    {...props}
  >
    {children}
    <IconPrimitive asChild>
      <ChevronDown className="h-4 w-4 opacity-50" />
    </IconPrimitive>
  </TriggerPrimitive>
));
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName;

type SelectScrollUpButtonProps = React.ComponentPropsWithoutRef<
  typeof SelectPrimitive.ScrollUpButton
> &
  WithDomStyling;

const SelectScrollUpButton = React.forwardRef<
  HTMLDivElement,
  SelectScrollUpButtonProps
>(({ className, ...props }, ref) => (
  <ScrollUpPrimitive
    ref={ref}
    className={cn('flex cursor-default items-center justify-center py-1', className)}
    {...props}
  >
    <ChevronUp className="h-4 w-4" />
  </ScrollUpPrimitive>
));
SelectScrollUpButton.displayName = SelectPrimitive.ScrollUpButton.displayName;

type SelectScrollDownButtonProps = React.ComponentPropsWithoutRef<
  typeof SelectPrimitive.ScrollDownButton
> &
  WithDomStyling;

const SelectScrollDownButton = React.forwardRef<
  HTMLDivElement,
  SelectScrollDownButtonProps
>(({ className, ...props }, ref) => (
  <ScrollDownPrimitive
    ref={ref}
    className={cn('flex cursor-default items-center justify-center py-1', className)}
    {...props}
  >
    <ChevronDown className="h-4 w-4" />
  </ScrollDownPrimitive>
));
SelectScrollDownButton.displayName = SelectPrimitive.ScrollDownButton.displayName;

type SelectContentProps = React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content> & WithDomStyling;

const SelectContent = React.forwardRef<
  HTMLDivElement,
  SelectContentProps
>(({ className, children, position = 'popper', ...props }, ref) => (
  <PortalPrimitive>
    <ContentPrimitive
      ref={ref}
      className={cn(
        'relative z-50 max-h-[--radix-select-content-available-height] min-w-[8rem] overflow-y-auto overflow-x-hidden rounded-xl border border-border bg-surface text-text shadow-lg data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 origin-[--radix-select-content-transform-origin]',
        position === 'popper' &&
          'data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1',
        className
      )}
      position={position}
      {...props}
    >
      <SelectScrollUpButton />
      <ViewportPrimitive
        className={cn(
          'p-1',
          position === 'popper' &&
            'h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]'
        )}
      >
        {children}
      </ViewportPrimitive>
      <SelectScrollDownButton />
    </ContentPrimitive>
  </PortalPrimitive>
));
SelectContent.displayName = SelectPrimitive.Content.displayName;

type SelectLabelProps = React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label> & WithDomStyling;

const SelectLabel = React.forwardRef<
  HTMLDivElement,
  SelectLabelProps
>(({ className, ...props }, ref) => (
  <LabelPrimitive
    ref={ref}
    className={cn('py-1.5 pl-8 pr-2 text-sm font-semibold', className)}
    {...props}
  />
));
SelectLabel.displayName = SelectPrimitive.Label.displayName;

type SelectItemProps = React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item> & WithDomStyling;

const SelectItem = React.forwardRef<
  HTMLDivElement,
  SelectItemProps
>(({ className, children, ...props }, ref) => (
  <ItemPrimitive
    ref={ref}
    className={cn(
      'relative flex w-full cursor-default select-none items-center rounded-lg py-2 pl-8 pr-2 text-sm outline-none focus:bg-surface-hover data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
      className
    )}
    {...props}
  >
    <span className="absolute left-2 flex h-3.5 w-3.5 items-center justify-center">
      <ItemIndicatorPrimitive>
        <Check className="h-4 w-4" />
      </ItemIndicatorPrimitive>
    </span>

    <ItemTextPrimitive>{children}</ItemTextPrimitive>
  </ItemPrimitive>
));
SelectItem.displayName = SelectPrimitive.Item.displayName;

type SelectSeparatorProps = React.ComponentPropsWithoutRef<typeof SelectPrimitive.Separator> & WithDomStyling;

const SelectSeparator = React.forwardRef<
  HTMLDivElement,
  SelectSeparatorProps
>(({ className, ...props }, ref) => (
  <SeparatorPrimitive
    ref={ref}
    className={cn('-mx-1 my-1 h-px bg-divider', className)}
    {...props}
  />
));
SelectSeparator.displayName = SelectPrimitive.Separator.displayName;

export {
  Select,
  SelectGroup,
  SelectValue,
  SelectTrigger,
  SelectContent,
  SelectLabel,
  SelectItem,
  SelectSeparator,
  SelectScrollUpButton,
  SelectScrollDownButton,
};
