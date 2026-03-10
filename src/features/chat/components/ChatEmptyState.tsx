'use client';

import dynamic from 'next/dynamic';
import type { QuickPrompt } from '../types';
import useGoblinLoaderAnimation from '../hooks/useGoblinLoaderAnimation';

interface ChatEmptyStateProps {
  quickPrompts: QuickPrompt[];
  onPromptClick: (prompt: string) => void;
  prefersReducedMotion?: boolean;
}

const Lottie = dynamic(() => import('lottie-react'), { ssr: false });

const ChatEmptyState = ({
  quickPrompts,
  onPromptClick,
  prefersReducedMotion = false,
}: ChatEmptyStateProps) => {
  const animationData = useGoblinLoaderAnimation();

  return (
    <section className="flex flex-col items-center justify-center h-full w-full px-4 py-8">
      <div className="flex flex-col items-center max-w-2xl w-full space-y-6">
        {/* Lottie Animation or Icon */}
        <div className="w-24 h-24 mb-2">
          {!prefersReducedMotion && animationData ? (
            <Lottie
              animationData={animationData}
              loop
              autoplay
              style={{ width: '100%', height: '100%' }}
            />
          ) : (
            <div className="w-full h-full bg-primary/20 rounded-full flex items-center justify-center">
              <span className="text-5xl">🧠</span>
            </div>
          )}
        </div>

        {/* Heading and Subtitle */}
        <div className="text-center space-y-2">
          <h2 className="text-2xl md:text-3xl font-semibold text-text">
            What can I help you with?
          </h2>
          <p className="text-muted text-sm md:text-base">
            Choose a suggestion below or type your own question to get started.
          </p>
        </div>

        {/* Suggested Prompts Grid */}
        <div className="w-full grid grid-cols-1 sm:grid-cols-2 gap-3">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt.label}
              onClick={() => onPromptClick(prompt.prompt)}
              type="button"
              className="group relative overflow-hidden rounded-2xl border border-border bg-surface/50 hover:bg-surface-hover px-4 py-3 text-left transition-colors duration-200"
            >
              <div className="text-sm font-medium text-text group-hover:text-primary transition-colors">
                {prompt.label}
              </div>
              <p className="text-xs text-muted mt-1 line-clamp-2 group-hover:text-text/70 transition-colors">
                {prompt.prompt}
              </p>
              {/* Subtle hover effect */}
              <div className="absolute inset-0 -z-10 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          ))}
        </div>

        {/* Optional help text */}
        <div className="text-xs text-muted text-center pt-4">
          You can also paste links or upload files for analysis.
        </div>
      </div>
    </section>
  );
};

export default ChatEmptyState;
