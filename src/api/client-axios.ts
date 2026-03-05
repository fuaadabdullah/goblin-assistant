// Real implementation for apiClient using axios

import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8001';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const chatAPI = {
  // Simple chat endpoint (recommended - uses /api/chat)
  chat: async (messages: any[], model?: string) => {
    const response = await apiClient.post('/api/chat', {
      messages,
      model,
      stream: false,
    });
    return response.data;
  },

  // Create a new conversation
  createConversation: async (title?: string) => {
    const response = await apiClient.post('/chat/conversations', {
      title: title || 'New Conversation',
    });
    return response.data;
  },

  // Get conversation list
  getConversations: async (limit = 50) => {
    const response = await apiClient.get('/chat/conversations', {
      params: { limit },
    });
    return response.data;
  },

  // Get specific conversation
  getConversation: async (conversationId: string) => {
    const response = await apiClient.get(`/chat/conversations/${conversationId}`);
    return response.data;
  },

  // Send message to conversation
  sendMessage: async (
    conversationId: string,
    message: string,
    provider?: string,
    model?: string
  ) => {
    const response = await apiClient.post(
      `/chat/conversations/${conversationId}/messages`,
      {
        message,
        provider,
        model,
        stream: false,
      }
    );
    return response.data;
  },

  // Contextual chat endpoint
  contextualChat: async (
    message: string,
    userId?: string,
    conversationId?: string,
    provider?: string,
    model?: string
  ) => {
    const response = await apiClient.post('/chat/contextual-chat', {
      message,
      user_id: userId,
      conversation_id: conversationId,
      provider,
      model,
      stream: false,
      enable_context_assembly: true,
    });
    return response.data;
  },

  // OpenAI-compatible chat completions
  chatCompletion: async (messages: any[], model?: string, stream = false) => {
    const response = await apiClient.post('/chat/completions', {
      messages,
      model,
      stream,
    });
    return response.data;
  },

  // Update conversation title
  updateConversationTitle: async (conversationId: string, title: string) => {
    const response = await apiClient.put(`/chat/conversations/${conversationId}/title`, {
      title,
    });
    return response.data;
  },

  // Delete conversation
  deleteConversation: async (conversationId: string) => {
    const response = await apiClient.delete(`/chat/conversations/${conversationId}`);
    return response.data;
  },

  // Health check
  healthCheck: async () => {
    const response = await apiClient.get('/health');
    return response.data;
  },

  // Provider test
  testProviderConnection: async (provider: string) => {
    const response = await apiClient.post('/chat/test-provider', {
      provider,
    });
    return response.data;
  },
};

export default apiClient;
