// app/api/routing/status/route.ts
import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8004';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/routing/status`, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error(`Backend routing status failed: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Routing status error:', error);
    return NextResponse.json(
      { 
        available: false,
        error: error instanceof Error ? error.message : 'Failed to fetch routing status',
      },
      { status: 200 }
    );
  }
}
