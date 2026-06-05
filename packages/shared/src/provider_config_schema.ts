/**
 * TypeScript types for config/providers.toml — the SINGLE source of truth.
 *
 * These types mirror the Pydantic schema in provider_config.py.
 * The frontend imports the generated `config/providers.json` and
 * validates it at import time through the `validateProvidersJson` function.
 *
 * Run `make generate-providers-json` (or the Python script directly)
 * after editing `config/providers.toml` to regenerate `config/providers.json`.
 */

// ── Leaf types ─────────────────────────────────────────────────────────────

export interface ScoringWeights {
  latency: number;
  cost: number;
  reliability: number;
  bandwidth: number;
}

export interface ChainOfThoughtSuppression {
  suppress_for: string[];
  force_for: string[];
}

export interface CostOptimization {
  max_budget_per_hour: number;
  preferred_providers_under_budget: string[];
}

export interface Health {
  health_check_interval: number;
  timeout_seconds: number;
  retry_attempts: number;
}

export interface CostEntry {
  input_per1k: number;
  output_per1k: number;
}

export interface RateLimitEntry {
  requests_per_minute: number;
  tokens_per_minute: number;
  concurrency: number;
}

export interface Raptor {
  level: string;
  file: string;
  enable_cpu: boolean;
  enable_memory: boolean;
  sample_rate_ms: number;
  trace_exceptions: boolean;
  enable_dev_flags: boolean;
}

export interface DefaultConfig {
  timeout_ms: number;
  scoring_weights: ScoringWeights;
  chain_of_thought_suppression: ChainOfThoughtSuppression;
  cost_optimization: CostOptimization;
  health: Health;
  raptor: Raptor;
}

export interface LoadBalancingHealthChecks {
  ollama_health: string;
  router_health: string;
  timeout_seconds: number;
}

export interface LoadBalancingServerPriorities {
  primary_ollama: string;
  backup_router: string;
}

export interface LoadBalancing {
  enabled: boolean;
  strategy: string;
  health_check_interval: number;
  failure_threshold: number;
  recovery_threshold: number;
  failover_to_backup: boolean;
  max_failover_time: number;
  circuit_breaker_enabled: boolean;
  health_checks: LoadBalancingHealthChecks;
  server_priorities: LoadBalancingServerPriorities;
}

export interface ProviderConfigEntry {
  name: string;
  endpoint?: string;
  endpoint_env?: string | null;
  endpoint_fallback?: string | null;
  invoke_path?: string;
  api_key_env?: string | null;
  default_model?: string;
  default_deployment?: string | null;
  models?: string[];
  capabilities?: string[];
  priority_tier?: number;
  cost_score?: number;
  cost_input_per1k?: number;
  cost_output_per1k?: number;
  costs?: Record<string, CostEntry>;
  rate_limits?: Record<string, RateLimitEntry>;
  default_timeout_ms?: number;
  bandwidth_score?: number;
  rate_limit_per_min?: number;
  supports_cot?: boolean;
  cot_suppression_prompt?: string;
  supports_openai_tools?: boolean | null;
  requires_env?: string[] | null;
  project_env?: string | null;
  tier?: string;
  local_routing?: boolean;
  is_active?: boolean;
  display_name?: string | null;
  selectable_requires_env?: boolean;
  force_fallback?: boolean;
  hidden?: boolean;
}

export interface ModelAlias {
  provider: string;
  model: string;
}

export interface ModelDefaults {
  provider: string;
  max_tokens: number;
  temperature: number;
  supports_streaming: boolean;
}

export interface ProviderTomlConfig {
  default: DefaultConfig;
  load_balancing: LoadBalancing;
  provider_aliases: Record<string, string>;
  model_aliases: Record<string, ModelAlias>;
  visible_providers: string[];
  model_context_windows: Record<string, number>;
  providers: Record<string, ProviderConfigEntry>;
  model_defaults: Record<string, ModelDefaults>;
  model_budgets: Record<string, RateLimitEntry>;
}

// ── JSON-serializable subset (the shape of providers.json) ─────────────────

export interface JsonProviderEntry {
  endpoint?: string;
  endpoint_env?: string | null;
  endpoint_fallback?: string | null;
  api_key_env?: string | null;
  priority_tier?: number;
  capabilities?: string[];
  models?: string[];
  cost_score?: number;
  cost_input_per1k?: number;
  cost_output_per1k?: number;
  costs?: Record<string, CostEntry>;
  rate_limits?: Record<string, RateLimitEntry>;
  default_timeout_ms?: number;
  rate_limit_per_min?: number;
  display_name?: string;
  is_active?: boolean;
  invoke_path?: string | null;
}

export interface ProvidersJson {
  version: number;
  default_timeout_ms: number;
  model_budgets: Record<string, RateLimitEntry>;
  providers: Record<string, JsonProviderEntry>;
}

// ── Validator helper (zero-dependency runtime check) ───────────────────────

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === "string");
}

function isNumber(value: unknown): value is number {
  return typeof value === "number" && !Number.isNaN(value);
}

function isBoolean(value: unknown): value is boolean {
  return typeof value === "boolean";
}

/**
 * Validate a parsed providers.json file at import time.
 * Throws a descriptive error if validation fails.
 */
export function validateProvidersJson(raw: unknown): ProvidersJson {
  if (!isRecord(raw)) {
    throw new Error("providers.json: root must be an object");
  }

  const version = raw.version;
  if (version !== 2) {
    throw new Error(
      `providers.json: expected version=2, got ${String(version)}`,
    );
  }

  const defaultTimeout = raw.default_timeout_ms;
  if (!isNumber(defaultTimeout) || defaultTimeout <= 0) {
    throw new Error(
      `providers.json: invalid default_timeout_ms: ${String(defaultTimeout)}`,
    );
  }

  if (!isRecord(raw.model_budgets)) {
    throw new Error("providers.json: model_budgets must be an object");
  }

  if (!isRecord(raw.providers)) {
    throw new Error("providers.json: providers must be an object");
  }

  for (const [pid, provider] of Object.entries(raw.providers)) {
    if (!isRecord(provider)) {
      throw new Error(`providers.json: provider "${pid}" must be an object`);
    }

    if (
      !provider.endpoint &&
      !provider.endpoint_env &&
      !provider.api_key_env
    ) {
      // Allow providers without any of these (e.g. vertex_ai with project-based auth)
      // but warn about it
      console.warn(
        `providers.json: provider "${pid}" has no endpoint or api_key_env`,
      );
    }
  }

  return raw as ProvidersJson;
}

/**
 * Default values for runtime use when config is not loaded yet.
 */
export const DEFAULT_PROVIDERS_JSON: ProvidersJson = {
  version: 2,
  default_timeout_ms: 12000,
  model_budgets: {},
  providers: {},
};
