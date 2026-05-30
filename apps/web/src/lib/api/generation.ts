import { postFrontend } from './shared';
import type { ChatMessage, ChatCompletionResponse } from '../../types/api';

export const generationMethods = {
  async generate(prompt: string, model?: string) {
    return postFrontend('/api/generate', { prompt, model });
  },

  async chatCompletion(messages: ChatMessage[], model?: string, _streaming?: boolean) {
    const response = await postFrontend<ChatCompletionResponse & { content?: string }>(
      '/api/generate',
      { messages, model }
    );

    if (typeof response?.content === 'string') return response.content;
    const choice = response?.choices?.[0];
    return choice?.message?.content || response;
  },
};
