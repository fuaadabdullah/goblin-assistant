export interface ProviderSource {
  name?: string;
  id?: number;
  enabled?: boolean;
  configured?: boolean;
  env_var?: string;
  api_key?: string;
  base_url?: string;
  models?: unknown;
}

export interface ProviderDisplay {
  name: string;
  normalizedName: string;
  configured: boolean;
  env_var?: string | undefined;
  base_url?: string | undefined;
  models: string[];
}

export type ProviderGroupId = 'configured' | 'needs-setup' | 'local' | 'cloud' | 'other';

export interface ProviderGroup {
  id: ProviderGroupId;
  title: string;
  description: string;
  providers: ProviderDisplay[];
}
