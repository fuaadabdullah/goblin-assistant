import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { apiClient, apiEndpoints } from '../services/api-client';

export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: string;
  model?: string;
  cost?: number;
  tokens?: {
    prompt: number;
    completion: number;
    total: number;
  };
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: string;
  updatedAt: string;
  model: string;
  totalCost: number;
  totalTokens: number;
}

interface ChatState {
  sessions: ChatSession[];
  currentSessionId: string | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  createSession: (title?: string) => void;
  setCurrentSession: (sessionId: string) => void;
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateMessage: (messageId: string, updates: Partial<Message>) => void;
  deleteSession: (sessionId: string) => void;
  clearSession: (sessionId: string) => void;
  loadHistory: () => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  streamMessage: (content: string) => Promise<void>;
  clearError: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentSessionId: null,
      isLoading: false,
      error: null,

      createSession: (title = 'New Chat') => {
        const newSession: ChatSession = {
          id: `session_${Date.now()}`,
          title,
          messages: [],
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          model: 'gpt-4',
          totalCost: 0,
          totalTokens: 0,
        };

        set((state) => ({
          sessions: [...state.sessions, newSession],
          currentSessionId: newSession.id,
        }));
      },

      setCurrentSession: (sessionId: string) => {
        set({ currentSessionId: sessionId });
      },

      addMessage: (messageData) => {
        const messageId = `msg_${Date.now()}`;
        const message: Message = {
          ...messageData,
          id: messageId,
          timestamp: new Date().toISOString(),
        };

        set((state) => {
          const currentSession = state.sessions.find(s => s.id === state.currentSessionId);
          if (!currentSession) return state;

          const updatedMessages = [...currentSession.messages, message];
          const updatedSession = {
            ...currentSession,
            messages: updatedMessages,
            updatedAt: new Date().toISOString(),
            totalCost: currentSession.totalCost + (message.cost || 0),
            totalTokens: currentSession.totalTokens + (message.tokens?.total || 0),
          };

          return {
            sessions: state.sessions.map(s => 
              s.id === currentSession.id ? updatedSession : s
            ),
          };
        });
      },

      updateMessage: (messageId: string, updates: Partial<Message>) => {
        set((state) => {
          const currentSession = state.sessions.find(s => s.id === state.currentSessionId);
          if (!currentSession) return state;

          const updatedMessages = currentSession.messages.map(msg =>
            msg.id === messageId ? { ...msg, ...updates } : msg
          );

          return {
            sessions: state.sessions.map(s =>
              s.id === currentSession.id
                ? { ...s, messages: updatedMessages }
                : s
            ),
          };
        });
      },

      deleteSession: (sessionId: string) => {
        set((state) => ({
          sessions: state.sessions.filter(s => s.id !== sessionId),
          currentSessionId: state.currentSessionId === sessionId ? null : state.currentSessionId,
        }));
      },

      clearSession: (sessionId: string) => {
        set((state) => ({
          sessions: state.sessions.map(s =>
            s.id === sessionId
              ? { ...s, messages: [], totalCost: 0, totalTokens: 0 }
              : s
          ),
        }));
      },

      loadHistory: async () => {
        set({ isLoading: true, error: null });
        
        try {
          const sessions = await apiClient.get<ChatSession[]>(apiEndpoints.chat.history);
          
          set({
            sessions,
            isLoading: false,
            error: null,
          });

          // Set first session as current if none is set
          if (sessions.length > 0 && !get().currentSessionId) {
            set({ currentSessionId: sessions[0].id });
          }
        } catch (error: any) {
          const errorMessage = error.response?.data?.message || 'Failed to load chat history';
          set({
            sessions: [],
            isLoading: false,
            error: errorMessage,
          });
        }
      },

      sendMessage: async (content: string) => {
        const currentSessionId = get().currentSessionId;
        if (!currentSessionId) {
          get().createSession();
          return;
        }

        // Add user message
        get().addMessage({
          content,
          role: 'user',
        });

        set({ isLoading: true, error: null });

        try {
          const response = await apiClient.post<{ message: Message }>(
            apiEndpoints.chat.messages,
            { sessionId: currentSessionId, content }
          );

          // Add assistant response
          get().addMessage({
            content: response.message.content,
            role: 'assistant',
            model: response.message.model,
            cost: response.message.cost,
            tokens: response.message.tokens,
          });

          set({ isLoading: false });
        } catch (error: any) {
          const errorMessage = error.response?.data?.message || 'Failed to send message';
          set({
            isLoading: false,
            error: errorMessage,
          });
          
          // Add error message to chat
          get().addMessage({
            content: `Error: ${errorMessage}`,
            role: 'system',
          });
        }
      },

      streamMessage: async (content: string) => {
        const currentSessionId = get().currentSessionId;
        if (!currentSessionId) {
          get().createSession();
          return;
        }

        // Add user message
        get().addMessage({
          content,
          role: 'user',
        });

        set({ isLoading: true, error: null });

        try {
          const response = await fetch(`${apiClient['client'].defaults.baseURL}${apiEndpoints.chat.stream}`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${apiClient.getAuthToken()}`,
            },
            body: JSON.stringify({ sessionId: currentSessionId, content }),
          });

          if (!response.ok) {
            throw new Error('Failed to stream message');
          }

          const reader = response.body?.getReader();
          const decoder = new TextDecoder();
          let assistantMessage = '';

          // Add initial assistant message
          const initialMessageId = `msg_${Date.now()}`;
          get().addMessage({
            content: '',
            role: 'assistant',
          });

          while (reader) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') continue;

                try {
                  const parsed = JSON.parse(data);
                  if (parsed.content) {
                    assistantMessage += parsed.content;
                    
                    // Update the assistant message content
                    get().updateMessage(initialMessageId, {
                      content: assistantMessage,
                    });
                  }
                } catch (e) {
                  console.warn('Failed to parse SSE data:', e);
                }
              }
            }
          }

          set({ isLoading: false });
        } catch (error: any) {
          const errorMessage = error.response?.data?.message || 'Failed to stream message';
          set({
            isLoading: false,
            error: errorMessage,
          });
          
          // Add error message to chat
          get().addMessage({
            content: `Error: ${errorMessage}`,
            role: 'system',
          });
        }
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
      }),
    }
  )
);
