import * as React from 'react';
import { clsx } from 'clsx';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';
import { useTheme } from '../../theme/components/ThemeProvider';

interface HeaderProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function Header({ title, subtitle, actions, className }: HeaderProps) {
  const { theme, highContrast } = useTheme();

  return (
    <header 
      className={clsx(
        'border-b bg-background sticky top-0 z-50 backdrop-blur-sm bg-background/95',
        className
      )}
    >
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-4">
            <div>
              <h1 className="text-xl font-semibold text-foreground">
                {title || 'Goblin Assistant'}
              </h1>
              {subtitle && (
                <p className="text-sm text-muted-foreground">
                  {subtitle}
                </p>
              )}
            </div>
            {highContrast && (
              <Badge variant="secondary" className="ml-2">
                High Contrast
              </Badge>
            )}
          </div>
          
          <div className="flex items-center space-x-2">
            {actions}
            <Button 
              variant="outline" 
              size="sm"
              onClick={() => {
                // Theme toggle logic would go here
              }}
            >
              Theme: {theme}
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
}
