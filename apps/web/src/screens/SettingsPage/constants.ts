import type { ProviderGroupId } from './types';

export const DEFAULT_OPEN_PROVIDER_GROUPS: ProviderGroupId[] = ['configured', 'needs-setup'];

export const LOCAL_PROVIDER_HINTS = ['ollama', 'llamacpp', 'colab', 'local', 'gcp', 'mock'];

export const CLOUD_PROVIDER_HINTS = [
  'openai',
  'anthropic',
  'groq',
  'gemini',
  'google',
  'deepseek',
  'siliconeflow',
  'azure',
  'vertex',
  'aliyun',
  'together',
  'replicate',
  'huggingface',
  'cohere',
];
