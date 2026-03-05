/**
 * MSW (Mock Service Worker) server setup for tests
 * 
 * This file sets up API mocking for all frontend tests
 * Handlers can be overridden per-test using server.use()
 */

import { http, HttpResponse } from 'msw';

// Default handlers for common API endpoints
export const handlers = [
  // Auth endpoints
  http.post('/api/auth/login', async ({ request }) => {
    const body = await request.json() as { email: string; password: string };
    
    // Mock successful login
    if (body.email && body.password) {
      return HttpResponse.json({
        access_token: 'mock_token_' + Math.random(),
        token_type: 'bearer',
        user: {
          id: 'user_' + Math.random(),
          email: body.email,
        },
      });
    }
    
    return HttpResponse.json({ error: 'Invalid credentials' }, { status: 401 });
  }),

  http.post('/api/auth/register', async ({ request }) => {
    const body = await request.json() as { email: string; password: string };
    
    // Mock successful registration
    if (body.email && body.password) {
      return HttpResponse.json({
        access_token: 'mock_token_' + Math.random(),
        token_type: 'bearer',
        user: {
          id: 'user_' + Math.random(),
          email: body.email,
        },
      });
    }
    
    return HttpResponse.json({ error: 'Registration failed' }, { status: 400 });
  }),

  // Chat endpoints
  http.post('/api/chat/create', async () => {
    return HttpResponse.json({
      conversation_id: 'conv_' + Math.random(),
      title: 'New Conversation',
      created_at: new Date().toISOString(),
    });
  }),

  http.post('/api/chat/:conversationId/message', async () => {
    return HttpResponse.json({
      message_id: 'msg_' + Math.random(),
      response: 'This is a mock response from the AI',
      provider: 'mock',
      model: 'mock-model',
      timestamp: new Date().toISOString(),
    });
  }),

  // Health check
  http.get('/api/health', () => {
    return HttpResponse.json({ status: 'ok' });
  }),
];

