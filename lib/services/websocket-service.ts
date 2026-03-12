'use client';

let _socket: WebSocket | null = null;
let _lastMessageAt: string | null = null;

const WS_READY_STATE: Record<number, string> = {
  [WebSocket.CONNECTING]: 'connecting',
  [WebSocket.OPEN]: 'connected',
  [WebSocket.CLOSING]: 'closing',
  [WebSocket.CLOSED]: 'disconnected',
};

export const websocketService = {
  connect: async (url: string, onMessage: (data: unknown) => void) => {
    if (_socket && _socket.readyState === WebSocket.OPEN) {
      _socket.close();
    }

    return new Promise<{ success: boolean; connection: { id: string; status: string; url: string } }>(
      (resolve, reject) => {
        const ws = new WebSocket(url);
        _socket = ws;

        ws.onopen = () => {
          resolve({
            success: true,
            connection: { id: `ws-${Date.now().toString(36)}`, status: 'connected', url },
          });
        };

        ws.onmessage = (event) => {
          _lastMessageAt = new Date().toISOString();
          try {
            onMessage(JSON.parse(event.data as string));
          } catch {
            onMessage(event.data);
          }
        };

        ws.onerror = () => reject(new Error('WebSocket connection failed'));
      },
    );
  },

  disconnect: async () => {
    if (_socket) {
      _socket.close();
      _socket = null;
    }
    return { success: true };
  },

  send: async (data: unknown) => {
    if (!_socket || _socket.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected');
    }
    _socket.send(typeof data === 'string' ? data : JSON.stringify(data));
    return { success: true, messageId: `msg-${Date.now().toString(36)}` };
  },

  getStatus: async () => {
    const readyState = _socket?.readyState ?? WebSocket.CLOSED;
    return {
      success: true,
      status: WS_READY_STATE[readyState] ?? 'disconnected',
      lastMessageAt: _lastMessageAt ?? new Date().toISOString(),
    };
  },
};
