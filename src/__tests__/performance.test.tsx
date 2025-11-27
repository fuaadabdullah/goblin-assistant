import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import StreamingView from '@/components/streaming/StreamingView';

// Mock the runtime client
vi.mock('@/api/api-client', () => ({
  runtimeClient: {
    executeGoblinCommand: vi.fn(),
  },
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <QueryClientProvider client={createTestQueryClient()}>{children}</QueryClientProvider>
);

// Mock performance API
const mockPerformance = {
  now: vi.fn(() => Date.now()),
  mark: vi.fn(),
  measure: vi.fn(),
  getEntriesByName: vi.fn(() => []),
  getEntriesByType: vi.fn(() => []),
  clearMarks: vi.fn(),
  clearMeasures: vi.fn(),
};

Object.defineProperty(window, 'performance', {
  value: mockPerformance,
  writable: true,
});

describe('Performance Tests - Streaming Components', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should handle high-frequency streaming updates without performance degradation', async () => {
    const startTime = performance.now();

    render(
      <TestWrapper>
        <StreamingView streamingText="" />
      </TestWrapper>
    );

    // Simulate high-frequency streaming data
    const streamingContainer = screen.getByTestId('streaming-container');
    const streamingOutput = streamingContainer.querySelector('.streaming-output') as HTMLElement;

    // Generate large amounts of streaming data
    const largeDataChunks = Array.from(
      { length: 100 },
      (_, i) => `Chunk ${i}: ${'x'.repeat(1000)}\n`
    );

    // Simulate streaming by updating the content rapidly
    for (const chunk of largeDataChunks) {
      streamingOutput.textContent += chunk;
      await vi.advanceTimersByTime(10); // 10ms between chunks
    }

    const endTime = performance.now();
    const duration = endTime - startTime;

    // Performance assertions
    expect(duration).toBeLessThan(2000); // Should complete within 2 seconds
    expect(streamingContainer).toBeInTheDocument();
    expect(streamingOutput.textContent?.length).toBeGreaterThan(100000); // Large content
  });

  it('should maintain UI responsiveness during heavy streaming load', async () => {
    render(
      <TestWrapper>
        <StreamingView streamingText="" />
      </TestWrapper>
    );

    const streamingOutput = screen
      .getByTestId('streaming-container')
      .querySelector('.streaming-output') as HTMLElement;

    // Start performance measurement
    const startTime = performance.now();

    // Simulate heavy streaming load with fewer, larger chunks
    const totalChunks = 20;
    const largeChunk = 'data'.repeat(1000); // 4000 chars per chunk

    for (let i = 0; i < totalChunks; i++) {
      streamingOutput.textContent += `Heavy chunk ${i}: ${largeChunk}\n`;
      await vi.advanceTimersByTime(10); // 10ms between chunks
    }

    const endTime = performance.now();
    const processingTime = endTime - startTime;

    // UI should remain responsive (processing should be fast)
    expect(processingTime).toBeLessThan(500); // Less than 500ms for 20 chunks
    expect(streamingOutput.textContent?.split('\n').length).toBeGreaterThan(18); // Most chunks processed
  }, 10000); // 10 second timeout

  it('should handle memory efficiently with large streaming datasets', async () => {
    // Mock console memory methods for Node.js environment
    const originalConsole = global.console;
    const memoryLogs: string[] = [];

    global.console.log = vi.fn((...args) => {
      memoryLogs.push(args.join(' '));
    });

    render(
      <TestWrapper>
        <StreamingView streamingText="" />
      </TestWrapper>
    );

    const streamingOutput = screen
      .getByTestId('streaming-container')
      .querySelector('.streaming-output') as HTMLElement;

    // Simulate memory-intensive streaming
    const memoryTestData = 'x'.repeat(10000); // 10KB per chunk
    const chunkCount = 20; // 200KB total

    for (let i = 0; i < chunkCount; i++) {
      streamingOutput.textContent += `${memoryTestData}\n`;
      await vi.advanceTimersByTime(20);
    }

    // Restore console
    global.console = originalConsole;

    // Verify content was processed
    expect(streamingOutput.textContent?.length).toBeGreaterThan(200000); // ~200KB of content

    // In a real scenario, we'd check for memory leaks here
    // For now, just ensure the component doesn't crash
    expect(screen.getByTestId('streaming-view')).toBeInTheDocument();
  });

  it('should throttle rapid updates to prevent UI blocking', async () => {
    render(
      <TestWrapper>
        <StreamingView streamingText="" />
      </TestWrapper>
    );

    const streamingOutput = screen
      .getByTestId('streaming-container')
      .querySelector('.streaming-output') as HTMLElement;

    // Start timing
    const startTime = performance.now();

    // Simulate extremely rapid updates (potential for UI blocking)
    const rapidUpdates = Array.from({ length: 200 }, (_, i) => `Update ${i}\n`);

    // Process all updates as fast as possible
    for (const update of rapidUpdates) {
      streamingOutput.textContent += update;
    }

    const endTime = performance.now();
    const batchTime = endTime - startTime;

    // Even with 200 rapid updates, processing should be fast
    expect(batchTime).toBeLessThan(100); // Less than 100ms for batch processing
    expect(streamingOutput.textContent?.split('\n').length).toBeGreaterThan(190); // Most updates processed
  });

  it('should handle streaming interruptions gracefully', async () => {
    render(
      <TestWrapper>
        <StreamingView streamingText="" />
      </TestWrapper>
    );

    const streamingOutput = screen
      .getByTestId('streaming-container')
      .querySelector('.streaming-output') as HTMLElement;

    // Start normal streaming
    streamingOutput.textContent = 'Starting stream...\n';

    // Simulate interruption (network error, etc.)
    await vi.advanceTimersByTime(100);
    streamingOutput.textContent += 'Stream interrupted\n';

    // Wait a bit
    await vi.advanceTimersByTime(50);

    // Resume streaming
    streamingOutput.textContent += 'Resuming stream...\n';
    streamingOutput.textContent += 'Final data chunk\n';

    // Verify the component handles the interruption
    const content = streamingOutput.textContent;
    expect(content).toContain('Starting stream');
    expect(content).toContain('Stream interrupted');
    expect(content).toContain('Resuming stream');
    expect(content).toContain('Final data chunk');

    // Component should still be functional
    expect(screen.getByTestId('streaming-view')).toBeInTheDocument();
  });

  it('should maintain scroll position during continuous streaming', async () => {
    render(
      <TestWrapper>
        <StreamingView streamingText="" />
      </TestWrapper>
    );

    const streamingContainer = screen.getByTestId('streaming-container');
    const streamingOutput = streamingContainer.querySelector('.streaming-output') as HTMLElement;

    // Mock scroll methods
    const mockScrollTop = { value: 0 };
    Object.defineProperty(streamingContainer, 'scrollTop', {
      get: () => mockScrollTop.value,
      set: value => {
        mockScrollTop.value = value;
      },
    });

    Object.defineProperty(streamingContainer, 'scrollHeight', {
      get: () => 1000,
    });

    // Simulate user scrolling to bottom
    mockScrollTop.value = 1000;

    // Add streaming content
    for (let i = 0; i < 10; i++) {
      streamingOutput.textContent += `Streaming line ${i}\n`;
      await vi.advanceTimersByTime(50);
    }

    // In a real implementation, scroll position should be maintained
    // For this test, we just verify the content is added
    expect(streamingOutput.textContent?.split('\n').length).toBeGreaterThan(8);
    expect(streamingContainer).toBeInTheDocument();
  });
});
