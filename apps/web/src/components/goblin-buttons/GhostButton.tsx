/* React 17+ automatic JSX runtime (no default import required) */
import { getButtonClasses } from './buttonStyles';

type BaseButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { className?: string };

type GhostVariant = 'primary' | 'accent' | 'danger';

export function GhostButton({
  children,
  onClick,
  disabled = false,
  variant = 'primary',
  className = '',
  type = 'button',
  ...props
}: BaseButtonProps & { variant?: GhostVariant }) {
  const colorClasses: Record<GhostVariant, string> = {
    primary: 'border-primary text-primary hover:bg-primary/10',
    accent: 'border-accent text-accent hover:bg-accent/10',
    danger: 'border-danger text-danger hover:bg-danger/10',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      type={type}
      className={`${getButtonClasses('ghost', `${colorClasses[variant]} ${className}`)}`}
      {...props}
    >
      {children}
    </button>
  );
}
