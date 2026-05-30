import { useCallback, useMemo } from 'react';
import { useChatThreads } from './useChatThreads';
import type { ChatThread } from '../types';

export interface ThreadSelectionState {
  threads: ChatThread[];
  isThreadsLoading: boolean;
  activeThreadKey: string | null;
  activeThread: ChatThread | null;
  activeBackendThreadId: string | null;
  selectThread: (threadKey: string) => void;
  setActiveThreadKey: (key: string | null) => void;
}

export interface ThreadSelectionProps {
  activeThreadKey: string | null;
  onThreadSelected: (threadKey: string | null) => void;
}

/**
 * Manages thread selection and state
 */
export const useThreadSelection = (
  activeThreadKey: string | null,
  onThreadSelected: (threadKey: string | null) => void
): ThreadSelectionState => {
  const { threads, isLoading: isThreadsLoading } = useChatThreads();

  const activeThread = useMemo(
    () => threads.find((thread) => thread.threadKey === activeThreadKey) ?? null,
    [activeThreadKey, threads]
  );

  const activeBackendThreadId = useMemo(
    () => (activeThread?.source === 'backend' ? activeThread.id : null),
    [activeThread]
  );

  const selectThread = useCallback(
    (threadKey: string) => {
      onThreadSelected(threadKey);
    },
    [onThreadSelected]
  );

  return {
    threads,
    isThreadsLoading,
    activeThreadKey,
    activeThread,
    activeBackendThreadId,
    selectThread,
    setActiveThreadKey: onThreadSelected,
  };
};
