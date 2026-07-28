/**
 * Canonical provider IDs as they appear in config/providers.json and the backend registry.
 * Use these instead of raw string literals to avoid typos and enable refactoring.
 */
export const PROVIDER_IDS = {
  OPENAI: 'openai',
  ANTHROPIC: 'anthropic',
  GEMINI: 'gemini',
  DEEPSEEK: 'deepseek',
  GROQ: 'groq',
  SILICONEFLOW: 'siliconeflow',
  AZURE_OPENAI: 'azure_openai',
  ALIYUN: 'aliyun',
  TOGETHER: 'together',
  REPLICATE: 'replicate',
  HUGGINGFACE: 'huggingface',
  COHERE: 'cohere',
  OLLAMA_LOCAL: 'ollama_local',
  GCP_VLLM: 'gcp_vllm',
  GCP_VM: 'gcp_vm',
  MOCK: 'mock',
} as const;

export type ProviderId = (typeof PROVIDER_IDS)[keyof typeof PROVIDER_IDS];

/** Provider IDs that indicate a locally-hosted or self-managed backend. */
export const LOCAL_PROVIDER_IDS: readonly ProviderId[] = [
  PROVIDER_IDS.OLLAMA_LOCAL,
  PROVIDER_IDS.GCP_VLLM,
  PROVIDER_IDS.GCP_VM,
  PROVIDER_IDS.MOCK,
] as const;

/** Provider IDs that indicate a cloud/SaaS API. */
export const CLOUD_PROVIDER_IDS: readonly ProviderId[] = [
  PROVIDER_IDS.OPENAI,
  PROVIDER_IDS.ANTHROPIC,
  PROVIDER_IDS.GEMINI,
  PROVIDER_IDS.DEEPSEEK,
  PROVIDER_IDS.GROQ,
  PROVIDER_IDS.SILICONEFLOW,
  PROVIDER_IDS.AZURE_OPENAI,
  PROVIDER_IDS.ALIYUN,
  PROVIDER_IDS.TOGETHER,
  PROVIDER_IDS.REPLICATE,
  PROVIDER_IDS.HUGGINGFACE,
  PROVIDER_IDS.COHERE,
] as const;
