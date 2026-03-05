import { NextRequest, NextResponse } from 'next/server';

export async function GET(_request: NextRequest) {
  // Mock provider data with realistic values
  const providerData = {
    timestamp: new Date().toISOString(),
    providers: {
      "openai": {
        name: "OpenAI",
        status: "healthy",
        last_check: Date.now() - 30000, // 30 seconds ago
        latency_ms: 150,
        error: null,
        capabilities: ["text", "code", "embeddings"],
        models: ["gpt-4", "gpt-3.5-turbo"],
        priority_tier: 1,
        circuit_breaker: {
          state: "CLOSED",
          failure_count: 0,
          failure_threshold: 5,
          last_failure_time: 0,
          time_until_recovery: 0
        },
        performance: {
          avg_response_time: 142,
          min_response_time: 89,
          max_response_time: 423,
          p95_response_time: 287,
          error_rate: 0.3,
          total_requests: 15420,
          error_count: 47
        },
        health_score: 94
      },
      "anthropic": {
        name: "Anthropic",
        status: "healthy",
        last_check: Date.now() - 45000, // 45 seconds ago
        latency_ms: 189,
        error: null,
        capabilities: ["text", "reasoning"],
        models: ["claude-3-sonnet", "claude-3-haiku"],
        priority_tier: 1,
        circuit_breaker: {
          state: "CLOSED",
          failure_count: 0,
          failure_threshold: 5,
          last_failure_time: 0,
          time_until_recovery: 0
        },
        performance: {
          avg_response_time: 176,
          min_response_time: 112,
          max_response_time: 534,
          p95_response_time: 298,
          error_rate: 0.5,
          total_requests: 8934,
          error_count: 45
        },
        health_score: 91
      },
      "groq": {
        name: "Groq",
        status: "degraded",
        last_check: Date.now() - 120000, // 2 minutes ago
        latency_ms: 892,
        error: null,
        capabilities: ["text", "fast-inference"],
        models: ["llama-2-70b", "mixtral-8x7b"],
        priority_tier: 2,
        circuit_breaker: {
          state: "HALF_OPEN",
          failure_count: 2,
          failure_threshold: 5,
          last_failure_time: Date.now() - 300000, // 5 minutes ago
          time_until_recovery: 0
        },
        performance: {
          avg_response_time: 1247,
          min_response_time: 234,
          max_response_time: 3892,
          p95_response_time: 2134,
          error_rate: 3.2,
          total_requests: 5621,
          error_count: 180
        },
        health_score: 67
      }
    },
    summary: {
      total_providers: 3,
      healthy_providers: 2,
      unhealthy_providers: 0,
      open_circuit_breakers: 0,
      avg_latency: 410
    }
  };

  return NextResponse.json(providerData);
}
