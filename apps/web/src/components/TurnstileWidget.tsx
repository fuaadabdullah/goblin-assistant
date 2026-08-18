import { useEffect, useRef, useState } from 'react';
import type { MutableRefObject } from 'react';
import { devError, devWarn } from '@/utils/dev-log';

type TurnstileRenderOptions = {
  sitekey: string;
  callback: (token: string) => void;
  'error-callback'?: () => void;
  'expired-callback'?: () => void;
  theme: 'light' | 'dark' | 'auto';
  size: 'normal' | 'compact' | 'invisible';
  appearance: 'always';
};

interface TurnstileWidgetProps {
  siteKey: string;
  onVerify: (token: string) => void;
  mode?: 'managed' | 'invisible';
  theme?: 'light' | 'dark' | 'auto';
  size?: 'normal' | 'compact';
  onError?: ((error: string) => void) | undefined;
}

const TURNSTILE_SCRIPT_SELECTOR = 'script[src*="challenges.cloudflare.com/turnstile"]';
const TURNSTILE_SCRIPT_SRC = 'https://challenges.cloudflare.com/turnstile/v0/api.js';

declare global {
  interface Window {
    turnstile?: {
      render: (element: HTMLElement, options: TurnstileRenderOptions) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
      execute: (
        widgetId: string,
        options?: Partial<Pick<TurnstileRenderOptions, 'callback'>>
      ) => void;
      getResponse: (widgetId: string) => string;
    };
  }
}

const hasTurnstileScript = () => document.querySelector(TURNSTILE_SCRIPT_SELECTOR) !== null;

const loadTurnstileScript = (onLoad: () => void) => {
  const script = document.createElement('script');
  script.src = TURNSTILE_SCRIPT_SRC;
  script.async = true;
  script.defer = true;
  script.onload = onLoad;
  document.head.appendChild(script);
  return script;
};

const removeTurnstileWidget = (widgetIdRef: MutableRefObject<string | null>) => {
  if (widgetIdRef.current && window.turnstile) {
    window.turnstile.remove(widgetIdRef.current);
  }
};

const createHiddenContainer = () => {
  const container = document.createElement('div');
  container.style.display = 'none';
  document.body.appendChild(container);
  return container;
};

const renderInvisibleTurnstile = (
  siteKey: string,
  setToken: (token: string) => void,
  widgetIdRef: MutableRefObject<string | null>
) => {
  if (!window.turnstile) return;

  const container = createHiddenContainer();
  widgetIdRef.current = window.turnstile.render(container, {
    sitekey: siteKey,
    theme: 'auto',
    size: 'invisible',
    appearance: 'always',
    callback: (token: string) => {
      setToken(token);
    },
  });
};

const executeTurnstileWidget = (widgetIdRef: MutableRefObject<string | null>) =>
  new Promise<string>((resolve, reject) => {
    if (!widgetIdRef.current || !window.turnstile) {
      reject(new Error('Turnstile not initialized'));
      return;
    }

    try {
      window.turnstile.execute(widgetIdRef.current, {
        callback: (token: string) => {
          resolve(token);
        },
      });
    } catch (error) {
      reject(error);
    }
  });

const createManagedTurnstileOptions = ({
  siteKey,
  onVerify,
  mode,
  theme,
  size,
  onError,
}: {
  siteKey: string;
  onVerify: (token: string) => void;
  mode: 'managed' | 'invisible';
  theme: 'light' | 'dark' | 'auto';
  size: 'normal' | 'compact';
  onError?: ((error: string) => void) | undefined;
}): TurnstileRenderOptions => ({
  sitekey: siteKey,
  callback: (token: string) => {
    onVerify(token);
  },
  'error-callback': () => {
    devError('Turnstile verification failed');
    onError?.('Bot verification failed');
  },
  'expired-callback': () => {
    devWarn('Turnstile token expired');
    onError?.('Verification expired, please try again');
  },
  theme,
  size: mode === 'invisible' ? 'invisible' : size,
  appearance: 'always',
});

function useTurnstileLoader(onError?: (error: string) => void) {
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    if (hasTurnstileScript()) {
      setIsLoaded(true);
      return;
    }

    const script = loadTurnstileScript(() => {
      setIsLoaded(true);
    });

    script.onerror = () => {
      devError('Failed to load Turnstile script');
      onError?.('Failed to load bot protection');
    };
  }, [onError]);

  return isLoaded;
}

function renderManagedTurnstile({
  siteKey,
  onVerify,
  mode,
  theme,
  size,
  onError,
  containerRef,
  widgetIdRef,
}: {
  siteKey: string;
  onVerify: (token: string) => void;
  mode: 'managed' | 'invisible';
  theme: 'light' | 'dark' | 'auto';
  size: 'normal' | 'compact';
  onError?: ((error: string) => void) | undefined;
  containerRef: MutableRefObject<HTMLDivElement | null>;
  widgetIdRef: MutableRefObject<string | null>;
}) {
  if (!containerRef.current || !window.turnstile) return;

  try {
    widgetIdRef.current = window.turnstile.render(
      containerRef.current,
      createManagedTurnstileOptions({ siteKey, onVerify, mode, theme, size, onError })
    );
  } catch (error) {
    devError('Error rendering Turnstile:', error);
    onError?.('Failed to initialize bot protection');
  }
}

function useManagedTurnstile({
  isLoaded,
  siteKey,
  onVerify,
  mode,
  theme,
  size,
  onError,
  containerRef,
  widgetIdRef,
}: {
  isLoaded: boolean;
  siteKey: string;
  onVerify: (token: string) => void;
  mode: 'managed' | 'invisible';
  theme: 'light' | 'dark' | 'auto';
  size: 'normal' | 'compact';
  onError?: ((error: string) => void) | undefined;
  containerRef: MutableRefObject<HTMLDivElement | null>;
  widgetIdRef: MutableRefObject<string | null>;
}) {
  useEffect(() => {
    if (!isLoaded) return;

    renderManagedTurnstile({
      siteKey,
      onVerify,
      mode,
      theme,
      size,
      onError,
      containerRef,
      widgetIdRef,
    });

    return () => {
      removeTurnstileWidget(widgetIdRef);
    };
  }, [isLoaded, siteKey, onVerify, mode, theme, size, onError, containerRef, widgetIdRef]);
}

function useInvisibleTurnstile({
  isLoaded,
  siteKey,
  setToken,
  widgetIdRef,
}: {
  isLoaded: boolean;
  siteKey: string;
  setToken: (token: string) => void;
  widgetIdRef: MutableRefObject<string | null>;
}) {
  useEffect(() => {
    if (!isLoaded || !window.turnstile) return;

    renderInvisibleTurnstile(siteKey, setToken, widgetIdRef);

    return () => {
      removeTurnstileWidget(widgetIdRef);
    };
  }, [isLoaded, siteKey, setToken, widgetIdRef]);
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
  const isLoaded = useTurnstileLoader(onError);

  useManagedTurnstile({
    isLoaded,
    siteKey,
    onVerify,
    mode,
    theme,
    size,
    onError,
    containerRef,
    widgetIdRef,
  });

  if (mode === 'invisible') {
    return <div ref={containerRef} style={{ display: 'none' }} />;
  }

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

export function useTurnstile(siteKey: string) {
  const [token, setToken] = useState('');
  const widgetIdRef = useRef<string | null>(null);
  const isLoaded = useTurnstileLoader();

  useInvisibleTurnstile({
    isLoaded,
    siteKey,
    setToken,
    widgetIdRef,
  });

  const execute = async (): Promise<string> => executeTurnstileWidget(widgetIdRef);

  const reset = () => {
    if (widgetIdRef.current && window.turnstile) {
      window.turnstile.reset(widgetIdRef.current);
      setToken('');
    }
  };

  return { token, execute, reset };
}
