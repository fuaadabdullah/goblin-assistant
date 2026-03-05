/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}', './app/**/*.{js,ts,jsx,tsx}'],
  safelist: [
    'grid-cols-1',
    'md:grid-cols-12',
    'gap-2',
    'col-span-12',
    'md:col-span-6',
    'lg:col-span-3',
    'xl:col-span-3',
    'lg:col-span-4',
    'xl:col-span-4',
    'bg-primary',
    'bg-secondary',
    'bg-tertiary',
    'bg-elevated',
    'bg-hover',
    'text-primary',
    'text-secondary',
    'text-tertiary',
    'text-disabled',
    'accent-green',
    'accent-green-dim',
    'accent-green-bright',
    'accent-green-alpha',
    'success',
    'success-bg',
    'error',
    'error-bg',
    'warning',
    'warning-bg',
    'info',
    'info-bg',
    'border-subtle',
    'border-medium',
    'border-strong',
    'shadow-sm',
    'shadow-md',
    'shadow-lg',
    'shadow-xl',
    'glow-green',
    'glow-green-strong',
    'font-mono',
    'font-sans',
    'text-xs',
    'text-sm',
    'text-base',
    'text-lg',
    'text-xl',
    'text-2xl',
    'text-3xl',
    'leading-tight',
    'leading-normal',
    'leading-relaxed',
    'space-1',
    'space-2',
    'space-3',
    'space-4',
    'space-6',
    'space-8',
    'space-12',
    'space-16',
    'radius-sm',
    'radius-md',
    'radius-lg',
    'radius-xl',
    'transition-fast',
    'transition-base',
    'transition-slow',
    'z-base',
    'z-dropdown',
    'z-sticky',
    'z-modal',
    'z-toast',
    'z-tooltip',
  ],
  theme: {
    extend: {
      colors: {
        // GoblinOS Dark Theme Colors
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        
        // Primary Colors
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },

        // GoblinOS Specific Colors
        'bg-primary': '#0a0a0a',
        'bg-secondary': '#141414',
        'bg-tertiary': '#1e1e1e',
        'bg-elevated': '#282828',
        'bg-hover': '#323232',
        
        'text-primary': '#e0e0e0',
        'text-secondary': '#a0a0a0',
        'text-tertiary': '#707070',
        'text-disabled': '#4a4a4a',

        'accent-green': '#00ff88',
        'accent-green-dim': '#00cc6a',
        'accent-green-bright': '#00ffaa',
        'accent-green-alpha': 'rgba(0, 255, 136, 0.1)',

        // Status Colors
        success: '#00ff88',
        'success-bg': 'rgba(0, 255, 136, 0.15)',
        error: '#ff4444',
        'error-bg': 'rgba(255, 68, 68, 0.15)',
        warning: '#ffaa00',
        'warning-bg': 'rgba(255, 170, 0, 0.15)',
        info: '#00aaff',
        'info-bg': 'rgba(0, 170, 255, 0.15)',

        // Border Colors
        'border-subtle': '#282828',
        'border-medium': '#3c3c3c',
        'border-strong': '#505050',

        // Shadow Colors
        'shadow-sm': '0 1px 2px rgba(0, 0, 0, 0.5)',
        'shadow-md': '0 2px 8px rgba(0, 0, 0, 0.6)',
        'shadow-lg': '0 4px 16px rgba(0, 0, 0, 0.7)',
        'shadow-xl': '0 8px 32px rgba(0, 0, 0, 0.8)',

        // Glow Colors
        'glow-green': '0 0 10px rgba(0, 255, 136, 0.3)',
        'glow-green-strong': '0 0 20px rgba(0, 255, 136, 0.5)',
      },
      boxShadow: {
        'goblin-glow': '0 6px 24px var(--glow-green)',
        'glow-green': '0 6px 24px var(--glow-green)',
        'glow-green-strong': '0 6px 24px var(--glow-green-strong)',
        'sm': '0 1px 2px rgba(0, 0, 0, 0.5)',
        'md': '0 2px 8px rgba(0, 0, 0, 0.6)',
        'lg': '0 4px 16px rgba(0, 0, 0, 0.7)',
        'xl': '0 8px 32px rgba(0, 0, 0, 0.8)',
      },
      dropShadow: {
        logo: '0 8px 28px rgba(0, 255, 136, 0.3)',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        'sm': '0.25rem', // 4px
        'md': '0.5rem', // 8px
        'lg': '0.75rem', // 12px
        'xl': '1rem', // 16px
      },
      fontFamily: {
        mono: [
          'SF Mono',
          'Monaco', 
          'Menlo',
          'Consolas',
          'Courier New',
          'monospace'
        ],
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'system-ui',
          'sans-serif'
        ],
      },
      fontSize: {
        xs: ['0.75rem', { lineHeight: '1.25' }], // 12px
        sm: ['0.875rem', { lineHeight: '1.5' }], // 14px
        base: ['1rem', { lineHeight: '1.5' }], // 16px
        lg: ['1.125rem', { lineHeight: '1.75' }], // 18px
        xl: ['1.25rem', { lineHeight: '1.75' }], // 20px
        '2xl': ['1.5rem', { lineHeight: '1.25' }], // 24px
        '3xl': ['1.875rem', { lineHeight: '1.25' }], // 30px
      },
      spacing: {
        1: '0.25rem', // 4px
        2: '0.5rem', // 8px
        3: '0.75rem', // 12px
        4: '1rem', // 16px
        6: '1.5rem', // 24px
        8: '2rem', // 32px
        12: '3rem', // 48px
        16: '4rem', // 64px
      },
      transitionTimingFunction: {
        'goblin-fast': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'goblin-base': 'cubic-bezier(0.4, 0, 0.2, 1)',
        'goblin-slow': 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      zIndex: {
        base: '0',
        dropdown: '1000',
        sticky: '1100',
        modal: '1200',
        toast: '1300',
        tooltip: '1400',
      },
    },
  },
  plugins: [],
};
