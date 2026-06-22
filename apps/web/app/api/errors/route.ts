import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const payload = await request.json().catch(() => null);

  // Keep the route intentionally thin: it exists to give browser-side error
  // reporting a stable same-origin target without forcing utilities to call fetch directly.
  console.warn('[api/errors] error_report', payload);

  return NextResponse.json({ ok: true }, { status: 202 });
}
