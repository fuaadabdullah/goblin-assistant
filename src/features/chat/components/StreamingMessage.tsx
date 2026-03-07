'use client';

import dynamic from 'next/dynamic';
import { useMemo } from 'react';
import type { ChatMessage } from '../types';

interface StreamingMessageProps {
  message: ChatMessage;
  isStreaming: boolean;
  prefersReducedMotion?: boolean;
}

const Lottie = dynamic(() => import('lottie-react'), { ssr: false });

const StreamingMessage = ({
  message,
  isStreaming,
  prefersReducedMotion = false,
}: StreamingMessageProps) => {
  const animationData = useMemo(() => {
    if (typeof window === 'undefined') return null;
    // Fallback to a simple text-based typing indicator in the future;
    // for now, we'll load from public/goblin_loader.json
    return null; // Will be loaded dynamically below
  }, []);

  return (
    <div className="space-y-2">
      <div className="whitespace-pre-wrap text-sm md:text-base leading-relaxed">
        {message.content}
      </div>

      {isStreaming && (
        <div className="mt-3 flex items-center gap-2">
          <div className="w-6 h-6">
            {!prefersReducedMotion ? (
              <Lottie
                animationData={animationData}
                loop
                autoplay
                style={{ width: '100%', height: '100%' }}
              />
            ) : (
              <div className="text-sm text-muted">Generating...</div>
            )}
          </div>
          <span className="text-xs text-muted animate-pulse">
            {prefersReducedMotion ? '' : 'Generating response...'}
          </span>
        </div>
      )}
    </div>
  );
};

export default StreamingMessage;
