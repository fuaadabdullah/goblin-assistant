// lib/store/chat-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Message, ChatSession, ChatRequest } from '../types';

interface ChatStore {
  messages: Message[];
  activeChatId: string | null;
  isStreaming: boolean;
  sessions: ChatSession[];

  actions: {
    sendMessage: (content: string) => Promise<void>;
    editMessage: (id: string, content: string) => void;
    clearChat: () => void;
    createSession: (title?: string) => string;
    loadSession: (sessionId: string) => void;
    deleteSession: (sessionId: string) => void;
    setActiveChat: (chatId: string | null) => void;
    addMessage: (message: Message) => void;
    updateStreamingMessage: (content: string) => void;
    stopStreaming: () => void;
  };
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set, get) => ({
      messages: [],
      activeChatId: null,
      isStreaming: false,
      sessions: [],

      actions: {
        sendMessage: async (content) => {
          const { activeChatId, actions } = get();

          if (!activeChatId) {
            // Create new session if none active
            const newSessionId = actions.createSession(content.slice(0, 50));
            set({ activeChatId: newSessionId });
          }

          set({ isStreaming: true });

          // Add user message
          const userMessage: Message = {
            id: Date.now().toString(),
            content,
            role: 'user',
            timestamp: new Date(),
          };
          actions.addMessage(userMessage);

          try {
            // Call API for streaming response
            const response = await fetch('/api/chat/stream', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                message: content,
                sessionId: activeChatId,
                stream: true,
              } as ChatRequest),
            });

            if (!response.ok) {
              throw new Error('Failed to send message');
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) return;

            let accumulatedContent = '';

            try {
              while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') {
                      actions.stopStreaming();
                      return;
                    }

                    try {
                      const parsed = JSON.parse(data);
                      if (parsed.content) {
                        accumulatedContent += parsed.content;
                        actions.updateStreamingMessage(accumulatedContent);
                      }
                    } catch (e) {
                      console.error('Failed to parse streaming data:', e);
                    }
                  }
                }
              }
            } finally {
              reader.releaseLock();
            }

            actions.stopStreaming();
          } catch (error) {
            console.error('Error sending message:', error);
            set({ isStreaming: false });

            // Add error message
            const errorMessage: Message = {
              id: Date.now().toString(),
              content: 'Sorry, I encountered an error. Please try again.',
              role: 'assistant',
              timestamp: new Date(),
            };
            actions.addMessage(errorMessage);
          }
        },

        editMessage: (id, content) => {
          set(state => ({
            messages: state.messages.map(msg =>
              msg.id === id ? { ...msg, content } : msg
            ),
          }));
        },

        clearChat: () => {
          set({ messages: [], isStreaming: false });
        },

        createSession: (title = 'New Chat') => {
          const newSession: ChatSession = {
            id: Date.now().toString(),
            title,
            messages: [],
            createdAt: new Date(),
            updatedAt: new Date(),
            isActive: true,
          };

          set(state => ({
            sessions: [newSession, ...state.sessions],
            activeChatId: newSession.id,
            messages: [],
          }));

          return newSession.id;
        },

        loadSession: (sessionId) => {
          const { sessions } = get();
          const session = sessions.find(s => s.id === sessionId);

          if (session) {
            set({
              activeChatId: sessionId,
              messages: session.messages,
              isStreaming: false,
            });
          }
        },

        deleteSession: (sessionId) => {
          set(state => ({
            sessions: state.sessions.filter(s => s.id !== sessionId),
            activeChatId: state.activeChatId === sessionId ? null : state.activeChatId,
            messages: state.activeChatId === sessionId ? [] : state.messages,
          }));
        },

        setActiveChat: (chatId) => {
          set({ activeChatId: chatId });
          if (chatId) {
            get().actions.loadSession(chatId);
          } else {
            set({ messages: [] });
          }
        },

        addMessage: (message) => {
          set(state => ({
            messages: [...state.messages, message],
          }));

          // Update session
          const { activeChatId } = get();
          if (activeChatId) {
            set(state => ({
              sessions: state.sessions.map(session =>
                session.id === activeChatId
                  ? {
                      ...session,
                      messages: [...session.messages, message],
                      updatedAt: new Date(),
                    }
                  : session
              ),
            }));
          }
        },

        updateStreamingMessage: (content) => {
          set(state => {
            const lastMessage = state.messages[state.messages.length - 1];
            if (lastMessage && lastMessage.role === 'assistant' && lastMessage.isPartial) {
              // Update existing partial message
              return {
                messages: [
                  ...state.messages.slice(0, -1),
                  { ...lastMessage, content },
                ],
              };
            } else {
              // Create new partial message
              const newMessage: Message = {
                id: Date.now().toString(),
                content,
                role: 'assistant',
                timestamp: new Date(),
                isPartial: true,
              };
              return {
                messages: [...state.messages, newMessage],
              };
            }
          });
        },

        stopStreaming: () => {
          set(state => ({
            isStreaming: false,
            messages: state.messages.map(msg =>
              msg.isPartial ? { ...msg, isPartial: false } : msg
            ),
          }));
        },
      },
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        activeChatId: state.activeChatId,
      }),
    }
  )
);
