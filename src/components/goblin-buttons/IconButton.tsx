/* React 17+ automatic JSX runtime (no default import required) */
import { getButtonClasses } from './buttonStyles';

type BaseButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & { className?: string };

type IconVariant = 'ghost' | 'primary' | 'danger';

export function IconButton({ children, onClick, disabled = false, variant = 'ghost', className = '', 'aria-label': ariaLabel, ...props }: BaseButtonProps & { variant?: IconVariant; 'aria-label': string }) {
  const variantClasses: Record<IconVariant, string> = {
    ghost: getButtonClasses('icon-ghost', className),
    primary: getButtonClasses('icon-primary', className),
    danger: getButtonClasses('icon-danger', className),
  };

  return (
    <button onClick={onClick} disabled={disabled} aria-label={ariaLabel} className={variantClasses[variant]} {...props}>
      {children}
    </button>
  );
}
