import { postFrontend } from './shared';
import type { ChatMessage, ChatCompletionResponse } from '../../types/api';

type GenerateResponse = ChatCompletionResponse & {
  content?: string;
  provider?: string;
  error?: string;
  detail?: string;
};

const isMockProvider = (provider: unknown): boolean =>
  typeof provider === 'string' && provider.trim().toLowerCase() === 'mock';

const assertRealRuntimeResponse = (response: GenerateResponse): GenerateResponse => {
  if (isMockProvider(response?.provider)) {
    throw new Error('Real model runtime is unavailable. Please try again later.');
  }
  return response;
};

export const generationMethods = {
  async generate(prompt: string, model?: string) {
    const response = await postFrontend<GenerateResponse>('/api/generate', { prompt, model });
    return assertRealRuntimeResponse(response);
  },

  async chatCompletion(messages: ChatMessage[], model?: string, _streaming?: boolean) {
    const response = assertRealRuntimeResponse(
      await postFrontend<GenerateResponse>('/api/generate', { messages, model })
    );

    if (typeof response?.content === 'string') return response.content;
    const choice = response?.choices?.[0];
    return choice?.message?.content || response;
  },
};
