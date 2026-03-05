export const BRAND_NAME = 'Goblin Assistant';

export const BRAND_HEADLINE = 'AI Gateway & Orchestration Platform';

export const BRAND_TAGLINE = 'Companies plug into Goblin once and never worry about LLM outages, runaway costs, or vendor lock-in again.';

export const HOME_VALUE_PROPS = [
  {
    title: 'Multi-LLM routing',
    body: 'Seamlessly route requests across providers.',
    icon: '🌍',
  },
  {
    title: 'Cost optimization',
    body: 'Detect anomalies and prevent runaway bills.',
    icon: '💰',
  },
  {
    title: 'Reliability & failover',
    body: 'Outage-proof routing with automatic fallbacks.',
    icon: '🛡️',
  },
  {
    title: 'Observability',
    body: 'Real-time logs, traces, and compliance audit trail.',
    icon: '📊',
  },
  {
    title: 'Security',
    body: 'Encryption, isolation, and policy enforcement.',
    icon: '🔒',
  },
  {
    title: 'RAG & agents',
    body: 'Orchestrate pipelines and multi-step workflows.',
    icon: '🚀',
  },
] as const;

export const HOME_EXAMPLE_CARDS = [
  {
    title: 'Route requests across 5 providers',
    body: 'GPT-4, Claude, Llama 2, PaLM, Cohere—with one API.',
    icon: '🔀',
  },
  {
    title: 'Detect cost anomalies',
    body: 'Alerts fire before your bill does. Save 40% overnight.',
    icon: '🚨',
  },
  {
    title: 'Never miss an outage',
    body: 'OpenAI down? Claude takes the lead automatically.',
    icon: '⚡',
  },
] as const;

export const CHAT_COMPOSER_PLACEHOLDER =
  'Route a request, trace a span, check cost limits, configure failover...';

export const CHAT_COMPOSER_TIP =
  'Try: route to Claude, check OpenAI costs, failover to Llama, see logs.';

export const CHAT_QUICK_PROMPTS = [
  {
    label: 'Route request',
    prompt: 'Route this request to the fastest available provider.',
  },
  {
    label: 'Check costs',
    prompt: 'Show me this month\'s LLM spending by provider. Flag anomalies.',
  },
  {
    label: 'View logs',
    prompt: 'Trace this request end-to-end. Show latency breakdown.',
  },
  {
    label: 'Set failover',
    prompt: 'Configure automatic failover from GPT-4 to Claude on outage.',
  },
] as const;

export const SEARCH_QUICK_QUERIES = [
  'OpenAI cost per request',
  'Claude confidence scores',
  'Provider failover rules',
  'Rate limit thresholds',
] as const;
