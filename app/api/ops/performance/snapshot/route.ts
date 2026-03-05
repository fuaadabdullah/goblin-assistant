import { NextRequest, NextResponse } from 'next/server';

export async function GET(_request: NextRequest) {
  // Mock performance data
  const performanceData = {
    timestamp: new Date().toISOString(),
    cache: {
      hit_ratio: 87.3,
      hits: 125430,
      misses: 18247,
      total_requests: 143677,
      memory_usage: "2.1 GB / 4.0 GB",
      connected_clients: "142"
    },
    performance: {
      avg_response_time: 234,
      avg_error_rate: 0.8,
      total_requests: 125430,
      total_errors: 1003
    },
    tasks: {
      total_tasks: 8945,
      completed_tasks: 8123,
      failed_tasks: 67,
      running_tasks: 124,
      queued_tasks: 631
    },
    usage: {
      streaming_tasks: 3456,
      non_streaming_tasks: 5489,
      streaming_percentage: 38.6
    }
  };

  return NextResponse.json(performanceData);
}
