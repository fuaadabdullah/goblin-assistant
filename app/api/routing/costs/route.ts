// app/api/routing/costs/route.ts
import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8004';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/routing/costs`, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error(`Backend routing costs failed: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Routing costs error:', error);
    return NextResponse.json(
      { 
        available: false,
        error: error instanceof Error ? error.message : 'Failed to fetch routing costs',
        cost_tracking: {
          hourly_budget: 10.0,
          current_spend: 0,
          remaining: 10.0,
          hour_start: new Date().toISOString(),
          request_count: 0,
          should_use_cheaper: false,
        }
      },
      { status: 200 }
    );
  }
}
