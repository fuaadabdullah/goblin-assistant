/**
 * UI Component Library — Reusable Atoms
 *
 * Centralized location for all base UI components.
 * All components enforce the design system: warm palette, consistent spacing, CVA-based variants.
 */

// Core interactive components
export { default as Button } from './Button';
export { default as IconButton } from './IconButton';
export { default as Badge } from './Badge';
export { default as Alert } from './Alert';

// Layout components
export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent } from './card';
export { default as Grid } from './Grid';

// Form components
export { Input } from './input';
export { Label } from './Label';
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
} from './Select';

// Dialog / Modal components
export {
  Dialog,
  DialogPortal,
  DialogOverlay,
  DialogClose,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from './Dialog';

// Utility components
export { default as Tooltip } from './Tooltip';

// Re-export types
export type { ButtonProps, ButtonVariantProps } from './Button';
export type { BadgeProps, BadgeVariantProps } from './Badge';
export type { IconButtonProps, IconButtonVariantProps } from './IconButton';
export type { AlertProps, AlertVariantProps } from './Alert';
export type { GridProps, GridVariantProps } from './Grid';
export type { InputProps, InputVariantProps } from './input';
