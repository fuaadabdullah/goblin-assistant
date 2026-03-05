import { NextRequest, NextResponse } from 'next/server';

export async function GET(_request: NextRequest) {
  // Mock system health data
  const healthData = {
    status: "healthy",
    timestamp: new Date().toISOString(),
    uptime: {
      seconds: 86400, // 1 day
      formatted: "1 day, 2 hours, 34 minutes"
    },
    components: {
      api: { status: "healthy" },
      routing: { status: "healthy" },
      database: { status: "healthy" },
      redis: { status: "healthy" },
      providers: { status: "healthy" },
      security: { status: "healthy" }
    },
    summary: {
      total_components: 6,
      healthy_components: 6,
      degraded_components: 0,
      warning_components: 0
    }
  };

  return NextResponse.json(healthData);
}
