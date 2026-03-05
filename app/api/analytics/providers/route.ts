// app/api/analytics/providers/route.ts
import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8004';

export async function GET() {
  try {
    // Fetch real-time routing health from backend
    const healthResponse = await fetch(`${BACKEND_URL}/routing/health`, {
      headers: {
        'Content-Type': 'application/json',
      },
      // Don't cache for real-time data
      cache: 'no-store',
    });

    if (!healthResponse.ok) {
      throw new Error(`Backend health check failed: ${healthResponse.status}`);
    }

    const healthData = await healthResponse.json();
    
    // Also fetch routing status for additional context
    const statusResponse = await fetch(`${BACKEND_URL}/routing/status`, {
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    });
    
    const statusData = statusResponse.ok ? await statusResponse.json() : null;
    
    // Transform backend data to frontend format
    const providers = Object.entries(healthData.providers || {}).map(([id, data]: [string, any]) => {
      // Provider name mapping
      const nameMap: Record<string, string> = {
        'ollama_gcp': 'GCP Ollama',
        'llamacpp_gcp': 'GCP llama.cpp',
        'ollama_kamatera': 'Kamatera Ollama',
        'llamacpp_kamatera': 'Kamatera llama.cpp',
        'openai': 'OpenAI',
        'anthropic': 'Anthropic',
        'groq': 'Groq',
        'google': 'Google Gemini',
        'siliconeflow': 'SiliconeFlow',
        'deepseek': 'DeepSeek',
      };
      
      // Model mapping
      const modelMap: Record<string, string[]> = {
        'ollama_gcp': ['qwen2.5:3b', 'llama3.2:1b'],
        'llamacpp_gcp': ['qwen2.5-3b-instruct'],
        'openai': ['gpt-4o', 'gpt-4o-mini'],
        'anthropic': ['claude-3-5-sonnet'],
        'groq': ['llama-3.1-8b-instant', 'mixtral-8x7b'],
        'google': ['gemini-pro'],
        'siliconeflow': ['Qwen/Qwen2.5-7B-Instruct'],
        'deepseek': ['deepseek-chat', 'deepseek-coder'],
      };

      return {
        id: id,
        name: nameMap[id] || id.charAt(0).toUpperCase() + id.slice(1).replace(/_/g, ' '),
        status: data.status || 'unknown',
        latency: data.avg_latency_ms || 0,
        uptime: data.status === 'healthy' ? 99.9 : data.status === 'degraded' ? 90 : 0,
        errorRate: data.consecutive_failures > 0 ? (data.consecutive_failures * 10) : 0,
        totalRequests: data.samples || 0,
        successRate: data.status === 'healthy' ? 99.9 : data.status === 'degraded' ? 90 : 0,
        lastError: data.last_error || null,
        models: modelMap[id] || [],
        lastCheck: data.last_check,
        lastSuccess: data.last_success,
      };
    });

    // Sort providers: healthy first, then by latency
    providers.sort((a, b) => {
      if (a.status === 'healthy' && b.status !== 'healthy') return -1;
      if (a.status !== 'healthy' && b.status === 'healthy') return 1;
      return a.latency - b.latency;
    });

    const healthyProviders = providers.filter(p => p.status === 'healthy');
    const degradedProviders = providers.filter(p => p.status === 'degraded');
    
    const overallHealth = healthyProviders.length > 0 ? 
      (degradedProviders.length > 0 ? 'degraded' : 'healthy') : 
      'unhealthy';
    
    const averageLatency = healthyProviders.length > 0
      ? healthyProviders.reduce((sum, p) => sum + p.latency, 0) / healthyProviders.length
      : 0;

    const providerData = {
      providers,
      overallHealth,
      totalActiveProviders: healthyProviders.length,
      averageLatency: Math.round(averageLatency * 100) / 100,
      totalErrors: providers.reduce((sum, p) => sum + p.errorRate, 0),
      lastHealthCheck: new Date().toISOString(),
      // Include routing status data
      routing: statusData ? {
        strategy: statusData.default_strategy,
        costTracking: statusData.cost_tracking,
        healthyProviders: statusData.healthy_providers,
        bestProviders: statusData.best_providers,
      } : null,
    };

    return NextResponse.json(providerData);

  } catch (error) {
    console.error('Analytics providers error:', error);
    
    // Return fallback data on error
    const fallbackData = {
      providers: [],
      overallHealth: 'unknown',
      totalActiveProviders: 0,
      averageLatency: 0,
      totalErrors: 0,
      lastHealthCheck: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Failed to fetch provider health',
    };
    
    return NextResponse.json(fallbackData, { status: 200 }); // Return 200 with error info
  }
}
