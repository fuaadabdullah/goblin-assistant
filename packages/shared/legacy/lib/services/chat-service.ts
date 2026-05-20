'use client';

import { apiClient } from './api-client';

export const chatService = {
  sendMessage: async (message: string, conversationId?: string) => {
    console.log('ChatService.sendMessage called with:', message);
    try {
      const response = await apiClient.post('/chat/stream', {
        message,
        conversationId,
        provider: 'openai',
        model: 'gpt-3.5-turbo',
      });

      if (response.success && response.data) {
        const data = response.data as any;
        return {
          success: true,
          message: data.message || 'Response received',
          conversationId: data.conversationId || conversationId || 'new-conversation',
        };
      }

      return {
        success: false,
        error: response.error?.message || 'Failed to send message',
      };
    } catch (error) {
      console.error('ChatService error:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },

  getConversationHistory: async (conversationId: string) => {
    try {
      const response = await apiClient.get(`/chat/history/${encodeURIComponent(conversationId)}`);

      if (response.success && response.data) {
        const data = response.data as { messages: Array<{ id: string; content: string; role: string; timestamp: string }> };
        return {
          success: true,
          messages: data.messages || [],
        };
      }

      return {
        success: false as const,
        messages: [],
        error: response.error?.message || 'Failed to load conversation history',
      };
    } catch (error) {
      console.error('ChatService.getConversationHistory error:', error);
      return {
        success: false as const,
        messages: [],
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },

  createNewConversation: async () => {
    try {
      const response = await apiClient.post('/chat/new');

      if (response.success && response.data) {
        const data = response.data as { conversationId: string };
        return {
          success: true,
          conversationId: data.conversationId,
        };
      }

      return {
        success: false as const,
        error: response.error?.message || 'Failed to create conversation',
      };
    } catch (error) {
      console.error('ChatService.createNewConversation error:', error);
      return {
        success: false as const,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  },
};
