export type { ChatMessage, ChatThread, ChatThreadSource } from '../../../domain/chat';

export interface QuickPrompt {
  label: string;
  prompt: string;
}

export type Mode = 'all' | 'finance' | 'learn' | 'general';
