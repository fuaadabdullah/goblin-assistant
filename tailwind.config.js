/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx}'],
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
  ],
  theme: {
    extend: {
      colors: {
        // Neutrals
        background: 'var(--background)',
        foreground: 'var(--foreground)',
        bg: 'var(--bg)',
        surface: 'var(--surface)',
        text: 'var(--text)',
        muted: 'var(--muted)',

        // Brand colors with variants
        primary: 'var(--primary)',
        'primary-300': 'var(--primary-300)',
        'primary-600': 'var(--primary-600)',

        accent: 'var(--accent)',
        'accent-300': 'var(--accent-300)',
        'accent-600': 'var(--accent-600)',

        cta: 'var(--cta)',
        'cta-300': 'var(--cta-300)',
        'cta-600': 'var(--cta-600)',

        // Semantic colors
        success: 'var(--success)',
        danger: 'var(--danger)',
        warning: 'var(--warning)',
        info: 'var(--info)',

        // Borders
        border: 'var(--border)',
        divider: 'var(--divider)',
      },
      boxShadow: {
        'goblin-glow': '0 6px 24px var(--glow-primary)',
        'glow-primary': '0 6px 24px var(--glow-primary)',
        'glow-accent': '0 6px 24px var(--glow-accent)',
        'glow-cta': '0 6px 24px var(--glow-cta)',
      },
      dropShadow: {
        logo: '0 8px 28px var(--glow-primary)',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [],
};
