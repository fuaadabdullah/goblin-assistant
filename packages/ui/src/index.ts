// ── Core interactive ────────────────────────────────────────────────
export { default as Button } from './button';
export { default as IconButton } from './icon-button';
export { default as Badge } from './badge';
export { default as Alert } from './alert';

// ── Layout ──────────────────────────────────────────────────────────
export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent } from './card';
export { default as Grid } from './grid';

// ── Form ────────────────────────────────────────────────────────────
export { Input } from './input';
export { Label } from './radix/label';
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
} from './radix/select';

// ── Dialog / Modal ──────────────────────────────────────────────────
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
} from './radix/dialog';

// ── Sheet (slide-over panel, Radix Dialog) ──────────────────────────
export {
  Sheet,
  SheetTrigger,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from './sheet';

// ── Tabs ────────────────────────────────────────────────────────────
export { Tabs, TabsList, TabsTrigger, TabsContent } from './tabs';

// ── Sidebar ─────────────────────────────────────────────────────────
export {
  Sidebar,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarItem,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarSeparator,
} from './sidebar';

// ── Identity ────────────────────────────────────────────────────────
export { default as Avatar } from './avatar';

// ── Feedback ────────────────────────────────────────────────────────
export { default as Spinner } from './spinner';
export { default as Skeleton } from './skeleton';

// ── Tooltip (utility) ───────────────────────────────────────────────
export { default as Tooltip } from './tooltip';

// ── Composed state components ───────────────────────────────────────
export { default as EmptyState } from './composed/empty-state';
export { default as InlineErrorState } from './composed/inline-error-state';
export { default as SectionLoadingState } from './composed/section-loading-state';
export { default as PageState } from './composed/page-state';
export { default as TristateWrapper } from './composed/tristate-wrapper';

// ── Theme system ────────────────────────────────────────────────────
export { ThemeProvider, useTheme } from './theme';
export type { ThemeProviderProps, ThemeContextValue, ThemeName } from './theme';

// ── Utility ─────────────────────────────────────────────────────────
export { cn } from './utils';

// ── Token types (for prop typing) ───────────────────────────────────
export type {
  ColorToken,
  SpacingToken,
  RadiusToken,
  ShadowToken,
  TypographyToken,
  MotionToken,
} from './tokens/tokens';
export { designTokens } from './tokens/tokens';

// ── Component prop types ────────────────────────────────────────────
export type { ButtonProps, ButtonVariantProps } from './button';
export type { BadgeProps, BadgeVariantProps } from './badge';
export type { IconButtonProps, IconButtonVariantProps } from './icon-button';
export type { AlertProps, AlertVariantProps } from './alert';
export type { EmptyStateProps } from './composed/empty-state';
export type { InlineErrorStateProps } from './composed/inline-error-state';
export type { PageStateProps } from './composed/page-state';
export type { SectionLoadingStateProps } from './composed/section-loading-state';
export type { TristateWrapperProps } from './composed/tristate-wrapper';
export type { GridProps, GridVariantProps } from './grid';
export type { InputProps, InputVariantProps } from './input';
export type { AvatarProps, AvatarVariantProps } from './avatar';
export type { SpinnerProps, SpinnerVariantProps } from './spinner';
export type { SkeletonProps, SkeletonVariantProps } from './skeleton';
export type { TabsProps } from './tabs';
export type { SidebarProps, SidebarItemProps } from './sidebar';
export type { SheetContentProps } from './sheet';
