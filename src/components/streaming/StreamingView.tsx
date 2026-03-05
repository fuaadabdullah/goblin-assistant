import { useState, useEffect, useRef } from 'react';
// CSS is imported globally in _app.tsx
import Button from '@/components/ui/Button';
import { TokenChunk, getNewChunk, toTokenChunk } from './streamingUtils';

interface Props {
  streamingText: string;
  isStreaming?: boolean;
}

// TokenChunk type is imported from streamingUtils

export default function StreamingView({ streamingText, isStreaming = false }: Props) {
  const [tokens, setTokens] = useState<TokenChunk[]>([]);
  const [currentText, setCurrentText] = useState('');
  const [showSummary, setShowSummary] = useState(false);
  const streamingRef = useRef<HTMLDivElement>(null);
  const lastChunkRef = useRef<string>('');

  useEffect(() => {
    // Always update current text
    setCurrentText(streamingText);

    // Only process new chunks when streaming
    if (!isStreaming) {
      return;
    }

    const newChunk = getNewChunk(lastChunkRef.current, streamingText);
    if (newChunk) {
      const newToken = toTokenChunk(newChunk, streamingText);
      setTokens(prev => [...prev, newToken]);
      lastChunkRef.current = streamingText;
    }
  }, [streamingText, isStreaming]);

  useEffect(() => {
    // Auto-scroll to bottom when new content arrives
    if (streamingRef.current) {
      streamingRef.current.scrollTop = streamingRef.current.scrollHeight;
    }
  }, [currentText]);

  useEffect(() => {
    // When streaming ends, show summary
    if (!isStreaming && streamingText) {
      setShowSummary(true);
    }
  }, [isStreaming, streamingText]);

  const renderTokenizedContent = () => {
    if (!isStreaming) {
      return <pre className="streaming-output">{currentText}</pre>;
    }

    return (
      <div className="streaming-output tokenized">
        {tokens.map((token, index) => (
          <span
            key={index}
            className={`token ${token.isCode ? 'code-token' : 'text-token'}`}
          >
            {token.text}
          </span>
        ))}
      </div>
    );
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(currentText);
      // Could add a toast notification here
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="streaming-view" aria-live="polite" data-testid="streaming-view">
      <div className="streaming-header" data-testid="streaming-header">
        <h3 data-testid="streaming-title">
          {showSummary ? 'Generated Content' : 'Streaming Output'}
        </h3>
        {isStreaming && (
          <div className="streaming-indicator" data-testid="streaming-indicator">
            ● Streaming
          </div>
        )}
        {!isStreaming && currentText && <Button onClick={copyToClipboard}>Copy Formatted</Button>}
      </div>
      <div className="streaming-container" ref={streamingRef} data-testid="streaming-container">
        {renderTokenizedContent()}
      </div>
    </div>
  );
}
