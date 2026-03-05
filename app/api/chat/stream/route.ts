// app/api/chat/stream/route.ts
import { NextRequest } from 'next/server';
import { aiService, AIProvider } from '../../../lib/services/ai-service';
import { handleApiError, createApiResponse, AppError } from 'lib/error-handler';

export async function POST(request: NextRequest) {
  try {
    let { message, provider, model, conversationId, temperature, maxTokens } = await request.json();

    if (!message) {
      throw new AppError('Message is required', 400);
    }

    // Validate provider
    const validProviders: AIProvider[] = ['openai', 'anthropic', 'google', 'ollama'];
    if (!validProviders.includes(provider)) {
      throw new AppError(`Invalid provider. Supported: ${validProviders.join(', ')}`, 400);
    }

    // Check if provider is available, fallback to ollama if openai not available
    if (!aiService.isProviderAvailable(provider)) {
      if (provider === 'openai') {
        // Fallback to ollama for testing
        provider = 'ollama';
      } else {
        throw new AppError(`${provider} is not configured or available`, 503);
      }
    }

    // Generate AI response
    const aiRequest = {
      message,
      provider,
      model: model || 'gpt-3.5-turbo', // Default model
      conversationId,
      temperature: temperature || 0.7,
      maxTokens: maxTokens || 1000,
      stream: false, // For now, we'll implement non-streaming
    };

    const aiResponse = await aiService.generateResponse(aiRequest);

    // Log usage to database (async, don't wait) - temporarily disabled for testing
    /*
    if (aiResponse.metadata.totalTokens && aiResponse.metadata.cost) {
      db.logUsage(
        'anonymous', // TODO: Get from auth
        provider,
        aiResponse.metadata.model,
        aiResponse.metadata.totalTokens,
        aiResponse.metadata.cost,
        aiResponse.metadata.latency || 0
      ).catch(error => {
        console.error('Failed to log usage:', error);
      });
    }
    */

    return createApiResponse(aiResponse);
  } catch (error) {
    return handleApiError(error);
  }
}
