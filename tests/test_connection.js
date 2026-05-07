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
</write_to_file>