// providers/WebSocketProvider.tsx
'use client';

import { createContext, useContext, useEffect, useRef, useState, useCallback, ReactNode } from 'react';
import { useAuth } from './AuthProvider';

export type WebSocketState = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WebSocketMessage {
  type: 'chat' | 'status' | 'error' | 'ping' | 'pong';
  payload: Record<string, unknown>;
  timestamp: number;
}

interface WebSocketContextType {
  state: WebSocketState;
  lastMessage: WebSocketMessage | null;
  sendMessage: (message: Omit<WebSocketMessage, 'timestamp'>) => void;
  connect: () => void;
  disconnect: () => void;
  isConnected: boolean;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

interface WebSocketProviderProps {
  children: ReactNode;
  url?: string;
}

export function WebSocketProvider({ children, url }: WebSocketProviderProps) {
  const { isAuthenticated, sessionToken } = useAuth();
  const [state, setState] = useState<WebSocketState>('disconnected');
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  // @ts-ignore - WebSocket is a browser API
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const pingIntervalRef = useRef<number | null>(null);

  const connect = useCallback(() => {
    if (!isAuthenticated || !sessionToken) {
      setState('disconnected');
      return;
    }

    // @ts-ignore - WebSocket is a browser API
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    setState('connecting');

    const wsUrl = url || `wss://${window.location.host}/ws/chat?token=${sessionToken}`;
    // @ts-ignore - WebSocket is a browser API
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setState('connected');
      console.log('WebSocket connected');

      // Start ping interval
      // @ts-ignore - setInterval returns Timeout in Node.js, number in browser
      pingIntervalRef.current = setInterval(() => {
        sendMessage({ type: 'ping', payload: {} });
      }, 30000); // Ping every 30 seconds
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastMessage(message);

        // Handle pong responses
        if (message.type === 'pong') {
          // Connection is alive
          return;
        }

        // Handle different message types
        switch (message.type) {
          case 'chat':
            // Chat messages are handled by the chat store
            break;
          case 'status':
            // Status updates
            break;
          case 'error':
            console.error('WebSocket error:', message.payload);
            break;
          default:
            console.log('Unknown message type:', message.type);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onclose = (event) => {
      setState('disconnected');
      console.log('WebSocket disconnected:', event.code, event.reason);

      // Clear ping interval
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }

      // Attempt reconnection if not a normal closure
      if (event.code !== 1000 && isAuthenticated) {
        // @ts-ignore - setTimeout returns Timeout in Node.js, number in browser
        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, 5000); // Reconnect after 5 seconds
      }
    };

    ws.onerror = (error) => {
      setState('error');
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  }, [isAuthenticated, sessionToken, url]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      // @ts-ignore - WebSocket is a browser API
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }

    setState('disconnected');
  }, []);

  const sendMessage = useCallback((message: Omit<WebSocketMessage, 'timestamp'>) => {
    // @ts-ignore - WebSocket is a browser API
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const fullMessage: WebSocketMessage = {
        ...message,
        timestamp: Date.now(),
      };
      // @ts-ignore - WebSocket is a browser API
      wsRef.current.send(JSON.stringify(fullMessage));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  }, []);

  // Connect when authenticated, disconnect when not
  useEffect(() => {
    if (isAuthenticated && sessionToken) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [isAuthenticated, sessionToken, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return (
    <WebSocketContext.Provider value={{
      state,
      lastMessage,
      sendMessage,
      connect,
      disconnect,
      isConnected: state === 'connected',
    }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within WebSocketProvider');
  }
  return context;
}
