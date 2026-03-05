'use client';

import React from 'react';
import { useTheme } from '../theme/components/ThemeProvider';

export const ThemePreview: React.FC = () => {
  const { theme, highContrast } = useTheme();

  const themeStyles = {
    default: {
      bg: 'bg-white border-gray-200',
      text: 'text-gray-900',
      accent: 'bg-blue-500',
    },
    dark: {
      bg: 'bg-gray-900 border-gray-700',
      text: 'text-white',
      accent: 'bg-blue-400',
    },
    light: {
      bg: 'bg-gray-50 border-gray-200',
      text: 'text-gray-900',
      accent: 'bg-blue-600',
    },
  };

  const currentTheme = themeStyles[theme as keyof typeof themeStyles] || themeStyles.default;

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium text-gray-900 dark:text-white">Current Theme Preview</h3>

      <div className="flex gap-4">
        <div className={`flex-1 p-4 rounded-lg border ${currentTheme.bg}`}>
          <div className="space-y-2">
            <div className={`h-4 rounded ${currentTheme.accent} w-3/4`}></div>
            <div className={`h-3 rounded bg-gray-200 ${currentTheme.text} w-full`}>Heading</div>
            <div className={`h-3 rounded bg-gray-100 ${currentTheme.text} w-5/6`}>Paragraph text</div>
            <div className={`h-6 rounded ${currentTheme.accent} w-1/2`}></div>
          </div>
        </div>

        <div className="flex flex-col justify-center">
          <div className="space-y-2">
            <div className="text-sm font-medium text-gray-500">Active Theme</div>
            <div className="text-lg font-semibold capitalize">{theme}</div>
            <div className="text-sm text-gray-500">
              {highContrast ? 'High Contrast: ON' : 'High Contrast: OFF'}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-gray-50 p-3 rounded-lg text-sm">
        <div className="font-medium text-gray-800 mb-1">Theme Features</div>
        <div className="text-gray-600">
          • Accessible color contrast<br />
          • Responsive design support<br />
          • Dark/light mode compatible
        </div>
      </div>
    </div>
  );
};

export default ThemePreview;
