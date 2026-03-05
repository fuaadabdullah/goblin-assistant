'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Globe } from 'lucide-react';
import { useI18n, locales, localeNames, type Locale } from '@/i18n';
import { Button } from '@/components/ui';

interface LanguageSwitcherProps {
  variant?: 'default' | 'compact' | 'minimal';
  className?: string;
}

export function LanguageSwitcher({ variant = 'default', className = '' }: LanguageSwitcherProps) {
  const { locale, setLocale, t, isRtl } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: Event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as HTMLElement)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close on escape key
  useEffect(() => {
    const handleKeyDown = (event: Event) => {
      if ((event as KeyboardEvent).key === 'Escape') {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleLocaleChange = (newLocale: Locale) => {
    setLocale(newLocale);
    setIsOpen(false);
  };

  if (variant === 'minimal') {
    return (
      <div className={`relative ${className}`} ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`p-2 rounded-lg hover:bg-bg-tertiary transition-colors ${isRtl ? 'rtl-flip' : ''}`}
          aria-label={t('settings.language')}
          aria-expanded={isOpen ? 'true' : 'false'}
        >
          <Globe className={`w-5 h-5 text-text-secondary ${isRtl ? 'transform scale-x-[-1]' : ''}`} />
        </button>

        {isOpen && (
          <div
            className={`absolute top-full mt-2 ${isRtl ? 'left-0' : 'right-0'} bg-bg-secondary border border-border-subtle rounded-lg shadow-lg py-1 min-w-[120px] z-50`}
            dir={isRtl ? 'rtl' : 'ltr'}
          >
            {locales.map((loc) => (
              <button
                key={loc}
                onClick={() => handleLocaleChange(loc)}
                className={`w-full px-4 py-2 text-left hover:bg-bg-tertiary transition-colors ${
                  locale === loc ? 'text-accent-green font-medium' : 'text-text-primary'
                } ${isRtl ? 'text-right' : 'text-left'}`}
                dir={loc === 'ar' ? 'rtl' : 'ltr'}
              >
                {localeNames[loc]}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (variant === 'compact') {
    return (
      <div className={`relative ${className}`} ref={dropdownRef}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-bg-tertiary transition-colors text-text-secondary hover:text-text-primary ${isRtl ? 'flex-row-reverse' : ''}`}
          aria-label={t('settings.language')}
          aria-expanded={isOpen ? 'true' : 'false'}
        >
          <Globe className={`w-4 h-4 ${isRtl ? 'transform scale-x-[-1]' : ''}`} />
          <span className="text-sm font-mono">{localeNames[locale]}</span>
        </button>

        {isOpen && (
          <div
            className={`absolute top-full mt-2 ${isRtl ? 'left-0' : 'right-0'} bg-bg-secondary border border-border-subtle rounded-lg shadow-lg py-1 min-w-[140px] z-50`}
            dir={isRtl ? 'rtl' : 'ltr'}
          >
            {locales.map((loc) => (
              <button
                key={loc}
                onClick={() => handleLocaleChange(loc)}
                className={`w-full px-4 py-2 text-left hover:bg-bg-tertiary transition-colors ${
                  locale === loc ? 'text-accent-green font-medium' : 'text-text-primary'
                } ${isRtl ? 'text-right' : 'text-left'}`}
                dir={loc === 'ar' ? 'rtl' : 'ltr'}
              >
                {localeNames[loc]}
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Default variant with full label
  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <Button
        variant="ghost"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 text-text-secondary hover:text-text-primary ${isRtl ? 'flex-row-reverse' : ''}`}
        aria-label={t('settings.language')}
        aria-expanded={isOpen}
      >
        <Globe className={`w-5 h-5 ${isRtl ? 'transform scale-x-[-1]' : ''}`} />
        <span className="font-mono">{localeNames[locale]}</span>
      </Button>

      {isOpen && (
        <div
          className={`absolute top-full mt-2 ${isRtl ? 'left-0' : 'right-0'} bg-bg-secondary border border-border-subtle rounded-lg shadow-lg py-2 min-w-[160px] z-50`}
          dir={isRtl ? 'rtl' : 'ltr'}
        >
          <div className="px-3 py-2 text-xs text-text-muted font-mono uppercase tracking-wide border-b border-border-subtle mb-1">
            {t('settings.language')}
          </div>
          {locales.map((loc) => (
            <button
              key={loc}
              onClick={() => handleLocaleChange(loc)}
              className={`w-full px-4 py-2 flex items-center gap-2 hover:bg-bg-tertiary transition-colors ${
                locale === loc ? 'text-accent-green font-medium' : 'text-text-primary'
              } ${isRtl ? 'flex-row-reverse justify-start' : ''}`}
              dir={loc === 'ar' ? 'rtl' : 'ltr'}
            >
              <span className="text-lg">{loc === 'ar' ? '🇸🇦' : loc === 'zh' ? '🇨🇳' : '🇺🇸'}</span>
              <span>{localeNames[loc]}</span>
              {locale === loc && (
                <span className={`${isRtl ? 'mr-auto' : 'ml-auto'} text-accent-green`}>✓</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default LanguageSwitcher;