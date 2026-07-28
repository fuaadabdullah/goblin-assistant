import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../utils';

const avatarVariants = cva(
  'inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full border border-border bg-surface-hover font-semibold text-text shadow-sm',
  {
    variants: {
      size: {
        sm: 'h-8 w-8 text-xs',
        md: 'h-10 w-10 text-sm',
        lg: 'h-12 w-12 text-base',
      },
    },
    defaultVariants: {
      size: 'md',
    },
  }
);

export type AvatarVariantProps = VariantProps<typeof avatarVariants>;

export interface AvatarProps extends React.HTMLAttributes<HTMLDivElement>, AvatarVariantProps {
  alt: string;
  fallback?: string;
  src?: string;
}

function initialsFromAlt(alt: string) {
  return alt
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
}

export function Avatar({ alt, fallback, src, size = 'md', className, ...props }: AvatarProps) {
  return (
    <div className={cn(avatarVariants({ size }), className)} {...props}>
      {src ? (
        <img src={src} alt={alt} className="h-full w-full object-cover" />
      ) : (
        <span aria-label={alt}>{fallback ?? initialsFromAlt(alt)}</span>
      )}
    </div>
  );
}

export default Avatar;
