// app/lib/services/ai-service.ts
import OpenAI from 'openai';
import Anthropic from '@anthropic-ai/sdk';
import { GoogleGenerativeAI } from '@google/generative-ai';

export type AIProvider = 'openai' | 'anthropic' | 'google' | 'ollama';

export interface AIRequest {
  message: string;
  provider: AIProvider;
  model: string;
  conversationId?: string;
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
}

export interface AIResponse {
  content: string;
  done: boolean;
  metadata: {
    provider: AIProvider;
    model: string;
    conversationId?: string;
    totalTokens?: number;
    cost?: number;
    latency?: number;
  };
}

export class AIService {
  private openai: OpenAI | null = null;
  private anthropic: Anthropic | null = null;
  private googleAI: GoogleGenerativeAI | null = null;

  constructor() {
    // Initialize clients if API keys are available
    if (process.env.OPENAI_API_KEY) {
      this.openai = new OpenAI({
        apiKey: process.env.OPENAI_API_KEY,
      });
    }

    if (process.env.ANTHROPIC_API_KEY) {
      this.anthropic = new Anthropic({
        apiKey: process.env.ANTHROPIC_API_KEY,
      });
    }

    if (process.env.GOOGLE_AI_API_KEY) {
      this.googleAI = new GoogleGenerativeAI(process.env.GOOGLE_AI_API_KEY);
    }
  }

  async generateResponse(request: AIRequest): Promise<AIResponse> {
    const startTime = Date.now();

    try {
      switch (request.provider) {
        case 'openai':
          return await this.generateOpenAIResponse(request, startTime);

        case 'anthropic':
          return await this.generateAnthropicResponse(request, startTime);

        case 'google':
          return await this.generateGoogleResponse(request, startTime);

        case 'ollama':
          return await this.generateOllamaResponse(request, startTime);

        default:
          throw new Error(`Unsupported provider: ${request.provider}`);
      }
    } catch (error) {
      console.error(`AI service error for ${request.provider}:`, error);

      // Return fallback response
      return {
        content: `Sorry, I'm having trouble connecting to ${request.provider}. Please try again later.`,
        done: true,
        metadata: {
          provider: request.provider,
          model: request.model,
          conversationId: request.conversationId,
          totalTokens: 0,
          cost: 0,
          latency: Date.now() - startTime,
        },
      };
    }
  }

  private async generateOpenAIResponse(request: AIRequest, startTime: number): Promise<AIResponse> {
    if (!this.openai) {
      throw new Error('OpenAI client not initialized');
    }

    const completion = await this.openai.chat.completions.create({
      model: request.model,
      messages: [{ role: 'user', content: request.message }],
      temperature: request.temperature || 0.7,
      max_tokens: request.maxTokens || 1000,
      stream: false, // For now, we'll implement non-streaming
    });

    const content = completion.choices[0]?.message?.content || '';
    const totalTokens = completion.usage?.total_tokens || 0;

    // Estimate cost (rough calculation)
    const cost = this.estimateOpenAICost(request.model, totalTokens);

    return {
      content,
      done: true,
      metadata: {
        provider: 'openai',
        model: request.model,
        conversationId: request.conversationId,
        totalTokens,
        cost,
        latency: Date.now() - startTime,
      },
    };
  }

  private async generateAnthropicResponse(request: AIRequest, startTime: number): Promise<AIResponse> {
    if (!this.anthropic) {
      throw new Error('Anthropic client not initialized');
    }

    const message = await this.anthropic.messages.create({
      model: request.model,
      max_tokens: request.maxTokens || 1000,
      temperature: request.temperature || 0.7,
      messages: [{ role: 'user', content: request.message }],
    });

    const content = message.content[0]?.type === 'text' ? message.content[0].text : '';
    const totalTokens = message.usage?.input_tokens || 0 + (message.usage?.output_tokens || 0);

    // Estimate cost (rough calculation)
    const cost = this.estimateAnthropicCost(request.model, totalTokens);

    return {
      content,
      done: true,
      metadata: {
        provider: 'anthropic',
        model: request.model,
        conversationId: request.conversationId,
        totalTokens,
        cost,
        latency: Date.now() - startTime,
      },
    };
  }

  private async generateGoogleResponse(request: AIRequest, startTime: number): Promise<AIResponse> {
    if (!this.googleAI) {
      throw new Error('Google AI client not initialized');
    }

    const model = this.googleAI.getGenerativeModel({ model: request.model });
    const result = await model.generateContent(request.message);
    const response = await result.response;
    const content = response.text();

    // Estimate tokens (rough approximation)
    const totalTokens = Math.ceil(content.length / 4); // Rough estimate
    const cost = this.estimateGoogleCost(request.model, totalTokens);

    return {
      content,
      done: true,
      metadata: {
        provider: 'google',
        model: request.model,
        conversationId: request.conversationId,
        totalTokens,
        cost,
        latency: Date.now() - startTime,
      },
    };
  }

  private async generateOllamaResponse(request: AIRequest, startTime: number): Promise<AIResponse> {
    // For Ollama, we'll make a direct HTTP request
    const ollamaUrl = process.env.OLLAMA_BASE_URL || 'http://localhost:11434';

    try {
      const response = await fetch(`${ollamaUrl}/api/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: request.model,
          prompt: request.message,
          stream: false,
        }),
      });

      if (!response.ok) {
        throw new Error(`Ollama API error: ${response.status}`);
      }

      const data = await response.json();
      const content = data.response || '';

      // Estimate tokens (rough approximation)
      const totalTokens = Math.ceil(content.length / 4);
      const cost = 0; // Ollama is local, no cost

      return {
        content,
        done: true,
        metadata: {
          provider: 'ollama',
          model: request.model,
          conversationId: request.conversationId,
          totalTokens,
          cost,
          latency: Date.now() - startTime,
        },
      };
    } catch (error) {
      console.error('Ollama request failed:', error);
      throw error;
    }
  }

  private estimateOpenAICost(model: string, tokens: number): number {
    // Rough cost estimates per 1K tokens (as of 2024)
    const rates: Record<string, number> = {
      'gpt-4': 0.03,
      'gpt-4-turbo': 0.01,
      'gpt-3.5-turbo': 0.002,
    };

    const rate = rates[model] || 0.01;
    return (tokens / 1000) * rate;
  }

  private estimateAnthropicCost(model: string, tokens: number): number {
    // Rough cost estimates per 1K tokens (as of 2024)
    const rates: Record<string, number> = {
      'claude-3-opus': 0.015,
      'claude-3-sonnet': 0.003,
      'claude-3-haiku': 0.00025,
    };

    const rate = rates[model] || 0.01;
    return (tokens / 1000) * rate;
  }

  private estimateGoogleCost(model: string, tokens: number): number {
    // Rough cost estimates per 1K tokens (as of 2024)
    const rates: Record<string, number> = {
      'gemini-pro': 0.00025,
      'gemini-pro-vision': 0.00025,
    };

    const rate = rates[model] || 0.001;
    return (tokens / 1000) * rate;
  }

  // Check if a provider is available
  isProviderAvailable(provider: AIProvider): boolean {
    switch (provider) {
      case 'openai':
        return !!this.openai;
      case 'anthropic':
        return !!this.anthropic;
      case 'google':
        return !!this.googleAI;
      case 'ollama':
        return true; // Assume Ollama is available if requested
      default:
        return false;
    }
  }

  // Get available providers
  getAvailableProviders(): AIProvider[] {
    const providers: AIProvider[] = ['openai', 'anthropic', 'google', 'ollama'];
    return providers.filter(provider => this.isProviderAvailable(provider));
  }
}

// Export singleton instance
export const aiService = new AIService();
