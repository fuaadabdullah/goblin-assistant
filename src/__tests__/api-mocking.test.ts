import { describe, it, expect } from 'vitest';

// Example of how to test API calls with MSW
describe('API Integration Tests', () => {
  it('should mock API calls successfully', async () => {
    // MSW automatically intercepts these calls
    const response = await fetch('http://127.0.0.1:8000/health');
    const data = await response.json();

    expect(data).toEqual({ status: 'healthy' });
  });

  it('should handle streaming responses', async () => {
    // Test streaming endpoints
    const response = await fetch('http://127.0.0.1:8000/execute/mock-task-123');
    const data = await response.json();

    expect(data.status).toBe('completed');
    expect(data.result).toBe('Task completed successfully');
  });
});
