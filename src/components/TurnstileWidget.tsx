import { useEffect, useRef, useState } from 'react';

interface TurnstileWidgetProps {
  siteKey: string;
  onVerify: (token: string) => void;
  mode?: 'managed' | 'invisible';
  theme?: 'light' | 'dark' | 'auto';
  size?: 'normal' | 'compact';
  onError?: (error: string) => void;
}

declare global {
  interface Window {
    turnstile?: {
      render: (element: HTMLElement, options: any) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
      execute: (widgetId: string, options?: any) => void;
      getResponse: (widgetId: string) => string;
    };
  }
}

export default function TurnstileWidget({
  siteKey,
  onVerify,
  mode = 'managed',
  theme = 'auto',
  size = 'normal',
  onError,
}: TurnstileWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    // Check if script already exists
    const existingScript = document.querySelector(
      'script[src*="challenges.cloudflare.com/turnstile"]'
    );

    if (existingScript) {
      setIsLoaded(true);
      return;
    }

    // Load Turnstile script
    const script = document.createElement('script');
    script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
    script.async = true;
    script.defer = true;

    script.onload = () => {
      setIsLoaded(true);
    };

    script.onerror = () => {
      console.error('Failed to load Turnstile script');
      onError?.('Failed to load bot protection');
    };

    document.head.appendChild(script);

    return () => {
      // Cleanup on unmount
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!isLoaded || !containerRef.current || !window.turnstile) return;

    // Render Turnstile widget
    try {
      widgetIdRef.current = window.turnstile.render(containerRef.current, {
        sitekey: siteKey,
        callback: (token: string) => {
          onVerify(token);
        },
        'error-callback': () => {
          console.error('Turnstile verification failed');
          onError?.('Bot verification failed');
        },
        'expired-callback': () => {
          console.warn('Turnstile token expired');
          onError?.('Verification expired, please try again');
        },
        theme: theme,
        size: mode === 'invisible' ? 'invisible' : size,
        appearance: 'always',
      });
    } catch (error) {
      console.error('Error rendering Turnstile:', error);
      onError?.('Failed to initialize bot protection');
    }
  }, [isLoaded, siteKey, onVerify, mode, theme, size, onError]);

  // For invisible mode, don't render anything
  if (mode === 'invisible') {
    return <div ref={containerRef} style={{ display: 'none' }} />;
  }

  // For managed mode, render the widget container
  return (
    <div
      ref={containerRef}
      className="turnstile-widget"
      style={{
        display: 'flex',
        justifyContent: 'center',
        marginTop: '1rem',
        marginBottom: '1rem',
      }}
    />
  );
}

// Export hook for programmatic access (useful for invisible mode)
export function useTurnstile(siteKey: string) {
  const [token, setToken] = useState<string>('');
  const widgetIdRef = useRef<string | null>(null);

  useEffect(() => {
    // Load script if not already loaded
    if (!document.querySelector('script[src*="challenges.cloudflare.com/turnstile"]')) {
      const script = document.createElement('script');
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js';
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);

      script.onload = () => {
        initializeTurnstile();
      };
    } else if (window.turnstile) {
      initializeTurnstile();
    }

    function initializeTurnstile() {
      if (!window.turnstile) return;

      const container = document.createElement('div');
      container.style.display = 'none';
      document.body.appendChild(container);

      widgetIdRef.current = window.turnstile.render(container, {
        sitekey: siteKey,
        size: 'invisible',
        callback: (token: string) => {
          setToken(token);
        },
      });
    }

    return () => {
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
      }
    };
  }, [siteKey]);

  const execute = async (): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (!widgetIdRef.current || !window.turnstile) {
        reject(new Error('Turnstile not initialized'));
        return;
      }

      // Set up one-time callback
      const tempCallback = (token: string) => {
        resolve(token);
      };

      try {
        window.turnstile.execute(widgetIdRef.current, {
          callback: tempCallback,
        });
      } catch (error) {
        reject(error);
      }
    });
  };

  const reset = () => {
    if (widgetIdRef.current && window.turnstile) {
      window.turnstile.reset(widgetIdRef.current);
      setToken('');
    }
  };

  return { token, execute, reset };
}
