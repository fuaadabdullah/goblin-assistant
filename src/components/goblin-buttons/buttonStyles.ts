export type ButtonStyleVariant = 'primary' | 'cta' | 'danger' | 'ghost' | 'icon-ghost' | 'icon-primary' | 'icon-danger';

export const baseButtonStyles = 'rounded-md text-sm font-semibold tracking-wide transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2';

export const getButtonClasses = (variant: ButtonStyleVariant, className = ''): string => {
  switch (variant) {
    case 'primary':
      return `${baseButtonStyles} px-4 py-2 bg-primary text-text shadow-md hover:shadow-lg hover:scale-[1.02] hover:bg-primary-600 active:scale-[0.98] ${className}`;
    case 'cta':
      return `${baseButtonStyles} px-4 py-2 bg-cta text-text shadow-md hover:shadow-lg hover:scale-[1.02] hover:bg-cta-600 active:scale-[0.98] ${className}`;
    case 'danger':
      return `${baseButtonStyles} px-4 py-2 bg-danger text-text shadow-md hover:shadow-lg hover:scale-[1.02] hover:bg-danger/90 active:scale-[0.98] ${className}`;
    case 'ghost':
      return `${baseButtonStyles} px-3 py-2 border border-border hover:bg-surface/50 hover:scale-[1.01] active:scale-[0.99] ${className}`;
    case 'icon-ghost':
      return `p-2 rounded-md hover:bg-surface/50 hover:scale-110 active:scale-95 transition-all duration-150 ${className}`;
    case 'icon-primary':
      return `p-2 rounded-md hover:bg-primary/15 transition-all duration-150 ${className}`;
    case 'icon-danger':
      return `p-2 rounded-md hover:bg-danger/15 transition-all duration-150 ${className}`;
    default:
      return `${baseButtonStyles} ${className}`;
  }
};
