'use client';

import dynamic from 'next/dynamic';
import type { ChatMessage } from '../types';
import MessageMarkdown from './MessageMarkdown';
import useGoblinLoaderAnimation from '../hooks/useGoblinLoaderAnimation';

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
  const animationData = useGoblinLoaderAnimation();

  return (
    <div className="space-y-2">
      <MessageMarkdown content={message.content} className="text-sm md:text-base leading-relaxed" />

      {isStreaming && (
        <div className="mt-3 flex items-center gap-2">
          <div className="w-6 h-6">
            {!prefersReducedMotion && animationData ? (
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
          {!prefersReducedMotion && (
            <span className="inline-flex items-center gap-0.5 text-xs text-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-current animate-bounce" />
              <span className="w-1.5 h-1.5 rounded-full bg-current animate-bounce [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-current animate-bounce [animation-delay:300ms]" />
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default StreamingMessage;
