import { Bot } from 'lucide-react';

interface LogoProps {
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'full' | 'simple' | 'emoji';
  className?: string;
  animated?: boolean;
  /**
   * If true, hides the logo from assistive tech (use when nearby text already
   * labels the product name to avoid repetition).
   */
  decorative?: boolean;
  /** Used when decorative is false. */
  ariaLabel?: string;
}

const sizeMap: Record<NonNullable<LogoProps['size']>, number> = {
  xs: 16,
  sm: 24,
  md: 32,
  lg: 48,
  xl: 64,
};

function LogoSimpleSvg({
  pixelSize,
  className,
  animated,
  decorative,
  ariaLabel,
}: {
  pixelSize: number;
  className: string;
  animated: boolean;
  decorative: boolean;
  ariaLabel: string;
}) {
  const commonProps = decorative
    ? { 'aria-hidden': true as const }
    : { role: 'img' as const, 'aria-label': ariaLabel };

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 48 48"
      width={pixelSize}
      height={pixelSize}
      focusable="false"
      className={`inline-block ${animated ? 'logo-transition' : ''} ${className}`}
      {...commonProps}
    >
      {!decorative ? <title>{ariaLabel}</title> : null}
      <circle cx="24" cy="24" r="22" fill="var(--color-brand-primary)" />

      {/* Eyes */}
      <circle cx="16" cy="20" r="3" fill="var(--color-bg)" />
      <circle cx="32" cy="20" r="3" fill="var(--color-bg)" />
      <circle cx="17" cy="19.5" r="1.2" fill="var(--color-text)" />
      <circle cx="33" cy="19.5" r="1.2" fill="var(--color-text)" />

      {/* Smile */}
      <path
        d="M 14 28 Q 24 34 34 28"
        stroke="var(--color-bg)"
        strokeWidth="2.5"
        fill="none"
        strokeLinecap="round"
      />

      {/* Tech accent */}
      <circle cx="38" cy="38" r="4" fill="var(--color-brand-secondary)" />
      <circle cx="38" cy="38" r="1.5" fill="var(--color-bg)" />
    </svg>
  );
}

function LogoFullSvg({
  pixelSize,
  className,
  animated,
  decorative,
  ariaLabel,
}: {
  pixelSize: number;
  className: string;
  animated: boolean;
  decorative: boolean;
  ariaLabel: string;
}) {
  const commonProps = decorative
    ? { 'aria-hidden': true as const }
    : { role: 'img' as const, 'aria-label': ariaLabel };

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      width={pixelSize}
      height={pixelSize}
      focusable="false"
      className={`inline-block ${animated ? 'logo-transition' : ''} ${className}`}
      {...commonProps}
    >
      {!decorative ? <title>{ariaLabel}</title> : null}
      {/* Background */}
      <circle
        cx="32"
        cy="32"
        r="30"
        fill="var(--color-surface-active)"
        stroke="var(--color-primary)"
        strokeWidth="2"
      />

      {/* Eyes */}
      <circle cx="22" cy="26" r="4" fill="var(--color-primary)" />
      <circle cx="42" cy="26" r="4" fill="var(--color-primary)" />
      <circle cx="23" cy="25" r="1.5" fill="var(--color-bg)" />
      <circle cx="43" cy="25" r="1.5" fill="var(--color-bg)" />

      {/* Ears */}
      <path
        d="M 12 24 Q 8 20 10 16 Q 12 20 14 22 Z"
        fill="var(--color-accent)"
        stroke="var(--color-primary)"
        strokeWidth="1"
      />
      <path
        d="M 52 24 Q 56 20 54 16 Q 52 20 50 22 Z"
        fill="var(--color-accent)"
        stroke="var(--color-primary)"
        strokeWidth="1"
      />

      {/* Nose */}
      <ellipse cx="32" cy="32" rx="3" ry="4" fill="var(--color-accent)" />

      {/* Mouth */}
      <path
        d="M 22 38 Q 32 44 42 38"
        stroke="var(--color-primary)"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
      />

      {/* Tech elements */}
      <path
        d="M 16 46 L 20 46 L 22 44"
        stroke="var(--color-brand-primary)"
        strokeWidth="1.5"
        fill="none"
        opacity="0.6"
      />
      <path
        d="M 48 46 L 44 46 L 42 44"
        stroke="var(--color-brand-primary)"
        strokeWidth="1.5"
        fill="none"
        opacity="0.6"
      />
      <circle cx="20" cy="46" r="1.5" fill="var(--color-brand-primary)" opacity="0.8" />
      <circle cx="44" cy="46" r="1.5" fill="var(--color-brand-primary)" opacity="0.8" />

      {/* Badge */}
      <g transform="translate(46, 44) scale(0.7)">
        <path
          d="M 0 -6 L 1.5 -1.5 L 6 0 L 1.5 1.5 L 0 6 L -1.5 1.5 L -6 0 L -1.5 -1.5 Z"
          fill="var(--color-brand-secondary)"
          stroke="var(--color-primary)"
          strokeWidth="0.8"
        />
        <circle cx="0" cy="0" r="2.5" fill="var(--color-bg)" />
      </g>
    </svg>
  );
}

/**
 * Theme-adaptive logo component with multiple variants and sizes.
 *
 * - Uses inline SVG so it blends with theme backgrounds (no JPEG box / halo).
 * - `decorative` can hide the logo from screen readers when adjacent text
 *   already labels the product name.
 */
export default function Logo({
  size = 'md',
  variant = 'full',
  className = '',
  animated = true,
  decorative = false,
  ariaLabel = 'Goblin Assistant',
}: LogoProps) {
  const pixelSize = sizeMap[size];

  if (variant === 'emoji') {
    return (
      <span
        className={`inline-block ${animated ? 'logo-animated' : ''} ${className}`}
        {...(decorative ? { 'aria-hidden': true } : { role: 'img', 'aria-label': ariaLabel })}
      >
        <Bot size={pixelSize} className="text-primary" aria-hidden="true" />
      </span>
    );
  }

  if (variant === 'simple') {
    return (
      <LogoSimpleSvg
        pixelSize={pixelSize}
        className={className}
        animated={animated}
        decorative={decorative}
        ariaLabel={ariaLabel}
      />
    );
  }

  return (
    <LogoFullSvg
      pixelSize={pixelSize}
      className={className}
      animated={animated}
      decorative={decorative}
      ariaLabel={ariaLabel}
    />
  );
}

