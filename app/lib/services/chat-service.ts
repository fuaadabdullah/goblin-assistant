// lib/services/chat-service.ts
import { apiClient } from './api-client';
import type { ChatRequest, ChatResponse, Message, ChatSession } from '../types';

export class ChatService {
  // Send a chat message
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await apiClient.post<ChatResponse>('/chat/completions', request);

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to send message');
    }

    return response.data;
  }

  // Stream chat response
  async *streamMessage(request: ChatRequest) {
    yield* apiClient.stream('/chat/stream', request);
  }

  // Get chat history
  async getChatHistory(sessionId: string): Promise<Message[]> {
    const response = await apiClient.get<{ messages: Message[] }>(`/chat/history/${sessionId}`);

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to get chat history');
    }

    return response.data.messages;
  }

  // Create new chat session
  async createSession(title?: string): Promise<ChatSession> {
    const response = await apiClient.post<ChatSession>('/chat/sessions', { title });

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to create session');
    }

    return response.data;
  }

  // Get all chat sessions
  async getSessions(): Promise<ChatSession[]> {
    const response = await apiClient.get<{ sessions: ChatSession[] }>('/chat/sessions');

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to get sessions');
    }

    return response.data.sessions;
  }

  // Delete chat session
  async deleteSession(sessionId: string): Promise<void> {
    const response = await apiClient.delete(`/chat/sessions/${sessionId}`);

    if (!response.success) {
      throw new Error(response.error?.message || 'Failed to delete session');
    }
  }

  // Update chat session
  async updateSession(sessionId: string, updates: Partial<ChatSession>): Promise<ChatSession> {
    const response = await apiClient.put<ChatSession>(`/chat/sessions/${sessionId}`, updates);

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to update session');
    }

    return response.data;
  }

  // Get chat session by ID
  async getSession(sessionId: string): Promise<ChatSession> {
    const response = await apiClient.get<ChatSession>(`/chat/sessions/${sessionId}`);

    if (!response.success || !response.data) {
      throw new Error(response.error?.message || 'Failed to get session');
    }

    return response.data;
  }
}

// Export singleton instance
export const chatService = new ChatService();