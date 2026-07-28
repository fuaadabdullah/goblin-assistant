import * as React from 'react';
import * as DialogPrimitive from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '../utils';

const Sheet = DialogPrimitive.Root;
const SheetClose = DialogPrimitive.Close;
const SheetTrigger = DialogPrimitive.Trigger;
const SheetPortal = DialogPrimitive.Portal;
const SheetOverlayPrimitive = DialogPrimitive.Overlay as React.ComponentType<any>;
const SheetContentPrimitive = DialogPrimitive.Content as React.ComponentType<any>;
const SheetTitle = DialogPrimitive.Title;
const SheetDescription = DialogPrimitive.Description;

const SheetOverlay = React.forwardRef<HTMLDivElement, any>(({ className, ...props }, ref) => (
  <SheetOverlayPrimitive
    ref={ref}
    className={cn(
      'goblin-motion-opacity fixed inset-0 z-50 bg-black/50 backdrop-blur-sm data-[state=closed]:opacity-0 data-[state=open]:opacity-100',
      className
    )}
    {...props}
  />
));
SheetOverlay.displayName = 'SheetOverlay';

export interface SheetContentProps extends React.HTMLAttributes<HTMLDivElement> {
  side?: 'left' | 'right' | 'top' | 'bottom';
}

const sideClasses = {
  left: 'left-0 top-0 h-full max-w-sm data-[state=closed]:slide-out-to-left data-[state=open]:slide-in-from-left',
  right:
    'right-0 top-0 h-full max-w-sm data-[state=closed]:slide-out-to-right data-[state=open]:slide-in-from-right',
  top: 'left-0 top-0 max-w-none data-[state=closed]:slide-out-to-top data-[state=open]:slide-in-from-top',
  bottom:
    'bottom-0 left-0 max-w-none data-[state=closed]:slide-out-to-bottom data-[state=open]:slide-in-from-bottom',
};

const SheetContent = React.forwardRef<HTMLDivElement, SheetContentProps>(
  ({ side = 'right', className, children, ...props }, ref) => (
    <SheetPortal>
      <SheetOverlay />
      <SheetContentPrimitive
        ref={ref}
        className={cn(
          'goblin-motion-transform fixed z-50 grid w-full gap-4 border-border bg-surface p-6 text-text shadow-xl',
          side === 'left' && 'border-r',
          side === 'right' && 'border-l',
          side === 'top' && 'border-b',
          side === 'bottom' && 'border-t',
          sideClasses[side],
          className
        )}
        {...props}
      >
        {children}
        <SheetClose className="goblin-focus-ring goblin-motion-opacity absolute right-4 top-4 rounded-md opacity-70 hover:opacity-100">
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </SheetClose>
      </SheetContentPrimitive>
    </SheetPortal>
  )
);
SheetContent.displayName = 'SheetContent';

const SheetHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('flex flex-col space-y-2 text-left', className)} {...props} />
);
SheetHeader.displayName = 'SheetHeader';

const SheetFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn('flex flex-col-reverse gap-3 sm:flex-row sm:justify-end', className)}
    {...props}
  />
);
SheetFooter.displayName = 'SheetFooter';

export {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetOverlay,
  SheetPortal,
  SheetTitle,
  SheetTrigger,
};
