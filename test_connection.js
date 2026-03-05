import { apiClient } from './app/lib/services/api-client.js';

async function testConnection() {
  console.log('Testing connection to backend...');

  try {
    // Test the test endpoint
    const testResponse = await apiClient.get('/test');
    console.log('Test endpoint response:', testResponse);

    // Test the chat stream endpoint
    const streamResponse = await fetch('http://localhost:8003/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: 'Hello, how are you?'
      })
    });

    if (streamResponse.ok) {
      console.log('Chat stream endpoint is accessible!');
    } else {
      console.error('Chat stream endpoint failed:', await streamResponse.text());
    }

  } catch (error) {
    console.error('Connection test failed:', error);
  }
}

testConnection();
<task_progress>
- [x] Explore goblin-assistant structure
- [x] Identify frontend and backend components
- [x] Understand current connection status
- [x] Make necessary fixes - updating API client to use correct backend URL
- [x] Make necessary fixes - updating chat page to use correct endpoint
- [x] Make necessary fixes - chat service endpoints are already correct
- [x] Make necessary fixes - adding streaming imports to chat router
- [x] Make necessary fixes - adding chat stream endpoint to chat router
- [x] Make necessary fixes - updating environment configuration
- [x] Make necessary fixes - creating proper .env.local file
- [x] Connect frontend to backend - starting backend server
- [x] Make necessary fixes - fixing import paths in main.py
- [x] Connect frontend to backend - restarting backend server with fixed imports
- [x] Connect frontend to backend - trying module import
- [x] Make necessary fixes - fixing circular import issue
- [x] Make necessary fixes - checking observability service for circular import
- [x] Make necessary fixes - removing circular import from observability service
- [x] Connect frontend to backend - restarting backend server after circular import fix
- [x] Make necessary fixes - checking retrieval service for circular import
- [x] Make necessary fixes - removing circular import from retrieval service
- [x] Make necessary fixes - moving observability import inside function
- [x] Connect frontend to backend - restarting backend server after all circular import fixes
- [x] Make necessary fixes - checking context assembly service import issue
- [x] Make necessary fixes - adding global instance to context assembly service
- [x] Connect frontend to backend - restarting backend server after context assembly fix
- [x] Make necessary fixes - fixing retrieval service lazy import in context assembly service
- [x] Connect frontend to backend - restarting backend server after retrieval service lazy import fix
- [x] Make necessary fixes - fixing retrieval service instantiation in context assembly service
- [x] Connect frontend to backend - restarting backend server after retrieval service instantiation fix
- [x] Connect frontend to backend - testing backend connection
- [x] Connect frontend to backend - testing chat stream endpoint
- [x] Connect frontend to backend - testing chat completions endpoint
- [x] Connect frontend to backend - starting frontend development server
- [x] Make necessary fixes - checking package.json for frontend scripts
- [x] Connect frontend to backend - trying npx next dev
- [x] Make necessary fixes - creating connection test file
- [ ] Run the application
</task_progress>
</write_to_file>