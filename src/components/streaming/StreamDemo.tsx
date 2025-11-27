// src/components/StreamDemo.tsx
import { useState } from 'react';
import { useProviderRouter } from '@/hooks/useProviderRouter';
import './StreamDemo.css';

export function StreamDemo() {
  const { routeTaskStream, checkStreamingHealth, connectionHealth } = useProviderRouter();
  const [text, setText] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fallbackMode, setFallbackMode] = useState<string | null>(null);

  const start = () => {
    setText('');
    setStreaming(true);
    setError(null);
    setFallbackMode(null);

    routeTaskStream(
      'chat',
      { prompt: 'Explain how Goblin OS works in 5 lines' },
      {
        onMeta: (meta: { fallback?: string; [key: string]: unknown }) => {
          console.log('meta', meta);
          if (meta.fallback) {
            setFallbackMode(meta.fallback);
          }
        },
        onChunk: (chunk: string | { data?: string; [key: string]: unknown }) => {
          // chunk may be object (delta) or string
          if (typeof chunk === 'string') setText(prev => prev + chunk);
          else if (chunk.data) setText(prev => prev + chunk.data);
          else setText(prev => prev + JSON.stringify(chunk));
        },
        onDone: () => {
          setStreaming(false);
        },
        onError: (err: { message?: string; [key: string]: unknown }) => {
          setError(err.message || 'Streaming error');
          setStreaming(false);
        },
      },
      { preferLocal: true }
    );
  };

  const checkHealth = async () => {
    const healthy = await checkStreamingHealth();
    console.log('Streaming health:', healthy ? 'healthy' : 'unhealthy');
  };

  return (
    <div className="stream-demo">
      <h3>Goblin Assistant Streaming Demo</h3>

      <div className="stream-controls">
        <button onClick={start} disabled={streaming}>
          {streaming ? 'Streaming...' : 'Start Stream'}
        </button>
        <button onClick={checkHealth}>Check Health</button>
      </div>

      <div className="connection-status">
        Connection:{' '}
        <span className={`connection-health ${connectionHealth || 'unknown'}`}>
          {connectionHealth || 'unknown'}
        </span>
        {fallbackMode && <span> | Mode: {fallbackMode}</span>}
      </div>

      {error && <div className="error-message">Error: {error}</div>}

      <div className="stream-output">{text || "Click 'Start Stream' to begin..."}</div>

      <div className="stream-info">
        This demo automatically falls back to polling if SSE is blocked by proxies. Check browser
        console for detailed streaming info.
      </div>
    </div>
  );
}
