'use client';

export const websocketService = {
  connect: async (url: string, _onMessage: (data: any) => void) => {
    console.log('WebSocketService.connect called with:', url);
    // Mock implementation
    return {
      success: true,
      connection: {
        id: 'mock-ws-connection',
        status: 'connected',
        url,
      },
    };
  },

  disconnect: async () => {
    console.log('WebSocketService.disconnect called');
    // Mock implementation
    return { success: true };
  },

  send: async (data: any) => {
    console.log('WebSocketService.send called with:', data);
    // Mock implementation
    return {
      success: true,
      messageId: Math.random().toString(36).substring(2, 9),
    };
  },

  getStatus: async () => {
    console.log('WebSocketService.getStatus called');
    // Mock implementation
    return {
      success: true,
      status: 'connected',
      lastMessageAt: new Date().toISOString(),
    };
  },
};
