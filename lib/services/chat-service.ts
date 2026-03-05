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
    console.log('ChatService.getConversationHistory called with:', conversationId);
    // Mock implementation
    return {
      success: true,
      messages: [
        {
          id: '1',
          content: 'Hello! How can I help you?',
          role: 'assistant',
          timestamp: new Date(Date.now() - 60000).toISOString(),
        },
        {
          id: '2',
          content: 'I need help with something',
          role: 'user',
          timestamp: new Date(Date.now() - 30000).toISOString(),
        },
      ],
    };
  },

  createNewConversation: async () => {
    console.log('ChatService.createNewConversation called');
    // Mock implementation
    return {
      success: true,
      conversationId: `conv-${Math.random().toString(36).substring(2, 9)}`,
    };
  },
};
