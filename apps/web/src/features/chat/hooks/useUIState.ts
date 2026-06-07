import type { KeyboardEvent, RefObject } from 'react';
import { useCallback, useRef, useState } from 'react';
import { useToast } from '../../../hooks/useToast';
import { chatClient } from '../api';
import { devError } from '@/utils/dev-log';
import type { PendingAttachment } from './useChatSession';

export interface UIState {
  input: string;
  authError: boolean;
  pendingAttachments: PendingAttachment[];
  inputRef: RefObject<HTMLTextAreaElement | null>;
  bottomRef: RefObject<HTMLDivElement | null>;
  isUploading: boolean;
  setInput: (value: string) => void;
  handleKeyDown: (e: KeyboardEvent<HTMLTextAreaElement>) => void;
  handlePromptClick: (prompt: string) => void;
  handleClearChat: () => void;
  handleFileSelected: (files: FileList) => void;
  removePendingAttachment: (fileId: string) => void;
}

export interface UIStateProps {
  onSendMessage: () => Promise<void>;
  onClearMessages: () => void;
}

/**
 * Manages UI state: input, auth errors, file attachments, keyboard handlers
 */
export const useUIState = ({ onSendMessage, onClearMessages }: UIStateProps): UIState => {
  const { showError, showInfo, showSuccess } = useToast();
  const [input, setInput] = useState('');
  const [authError, setAuthError] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<PendingAttachment[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        void onSendMessage();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        void onSendMessage();
      }
    },
    [onSendMessage]
  );

  const handlePromptClick = useCallback((prompt: string) => {
    setInput(prompt);
    inputRef.current?.focus();
  }, []);

  const handleClearChat = useCallback(() => {
    setInput('');
    setPendingAttachments([]);
    onClearMessages();
    inputRef.current?.focus();
  }, [onClearMessages]);

  const handleFileSelected = useCallback(
    (files: FileList) => {
      setIsUploading(true);
      showInfo(
        'Uploading attachments',
        `Preparing ${files.length} file${files.length === 1 ? '' : 's'}.`
      );
      const uploads = Array.from(files).map(async (file) => {
        try {
          const result = await chatClient.uploadFile(file);
          return result as PendingAttachment;
        } catch (err) {
          devError('file_upload_failed', err);
          showError('Upload failed', `We could not upload ${file.name}.`);
          return null;
        }
      });
      void Promise.all(uploads).then((results) => {
        const successful = results.filter((r): r is PendingAttachment => r !== null);
        if (successful.length > 0) {
          setPendingAttachments((prev) => [...prev, ...successful]);
          showSuccess(
            'Attachments ready',
            `${successful.length} file${successful.length === 1 ? '' : 's'} attached to your next message.`
          );
        }
        setIsUploading(false);
      });
    },
    [showError, showInfo, showSuccess]
  );

  const removePendingAttachment = useCallback((fileId: string) => {
    setPendingAttachments((prev) => prev.filter((a) => a.file_id !== fileId));
  }, []);

  return {
    input,
    setInput,
    authError,
    pendingAttachments,
    inputRef,
    bottomRef,
    isUploading,
    handleKeyDown,
    handlePromptClick,
    handleClearChat,
    handleFileSelected,
    removePendingAttachment,
  };
};
