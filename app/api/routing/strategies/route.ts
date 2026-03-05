// app/api/routing/strategies/route.ts
import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8004';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/routing/strategies`, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      throw new Error(`Backend routing strategies failed: ${response.status}`);
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Routing strategies error:', error);
    // Return default strategies on error
    return NextResponse.json({
      strategies: [
        {
          id: 'cost_optimized',
          name: 'Cost Optimized',
          description: 'Prioritize free/cheap providers (GCP → Groq → Cloud)',
          priority_order: ['ollama_gcp', 'llamacpp_gcp', 'groq', 'siliconeflow', 'deepseek', 'openai', 'anthropic'],
        },
        {
          id: 'quality_first',
          name: 'Quality First',
          description: 'Prioritize high-quality providers (Claude → GPT-4 → Cloud)',
          priority_order: ['anthropic', 'openai', 'groq', 'deepseek', 'ollama_gcp'],
        },
        {
          id: 'latency_optimized',
          name: 'Latency Optimized',
          description: 'Prioritize fastest providers (Groq → GCP → Cloud)',
          priority_order: ['groq', 'ollama_gcp', 'openai', 'anthropic'],
        },
        {
          id: 'local_first',
          name: 'Local First',
          description: 'Prioritize local/self-hosted providers for privacy',
          priority_order: ['ollama_gcp', 'llamacpp_gcp', 'groq', 'openai'],
        },
      ],
      default: 'cost_optimized',
    });
  }
}
