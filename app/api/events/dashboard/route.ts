// app/api/events/dashboard/route.ts

export async function GET() {
  // For now, return a simple SSE response
  // TODO: Implement proper streaming with ReadableStream when Next.js types are resolved

  const initialData = {
    type: 'connected',
    timestamp: new Date().toISOString(),
    message: 'Real-time dashboard updates connected',
  };

  const response = `data: ${JSON.stringify(initialData)}\n\n`;

  return new Response(response, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Cache-Control',
    },
  });
}
