export type MemoryCategory = 'preference' | 'project' | 'goal' | 'fact' | 'correction';

export interface Memory {
  id: string;
  text: string;
  category: MemoryCategory;
  importance: number;
  confidence: number;
  lastAccessed: Date;
  createdAt: Date;
  embedding: number[];
}

export interface MemoryPayloadLike {
  id?: string;
  memory_id?: string;
  text?: string;
  content?: string;
  fact_text?: string;
  category?: string;
  memory_type?: string;
  type?: string;
  importance?: number | string | null;
  salience_score?: number | string | null;
  confidence?: number | string | null;
  score?: number | string | null;
  lastAccessed?: string | Date | null;
  last_accessed_at?: string | Date | null;
  createdAt?: string | Date | null;
  created_at?: string | Date | null;
  embedding?: number[] | string | null;
  fact_embedding?: number[] | string | null;
}

const MEMORY_CATEGORY_ALIASES: Record<string, MemoryCategory> = {
  correction: 'correction',
  corrections: 'correction',
  decision: 'fact',
  fact: 'fact',
  facts: 'fact',
  instrument: 'fact',
  knowledge: 'fact',
  macro_event: 'fact',
  preference: 'preference',
  preferences: 'preference',
  project: 'project',
  project_state: 'project',
  projects: 'project',
  regulatory_constraint: 'fact',
  relationship: 'fact',
  relationships: 'fact',
  risk_signal: 'fact',
  goal: 'goal',
  goals: 'goal',
  task_signal: 'goal',
  task: 'goal',
};

const MEMORY_CATEGORY_SET = new Set<MemoryCategory>([
  'preference',
  'project',
  'goal',
  'fact',
  'correction',
]);

function parseMemoryDate(value: string | Date | null | undefined): Date {
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? new Date(0) : value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? new Date(0) : parsed;
  }
  return new Date(0);
}

function parseMemoryEmbedding(value: number[] | string | null | undefined): number[] {
  if (Array.isArray(value)) {
    return value
      .map((item) => Number(item))
      .filter((item) => Number.isFinite(item));
  }
  if (typeof value === 'string' && value.trim()) {
    try {
      const parsed = JSON.parse(value) as unknown;
      if (Array.isArray(parsed)) {
        return parsed
          .map((item) => Number(item))
          .filter((item) => Number.isFinite(item));
      }
    } catch {
      return [];
    }
  }
  return [];
}

export function isMemoryCategory(value: unknown): value is MemoryCategory {
  return typeof value === 'string' && MEMORY_CATEGORY_SET.has(value as MemoryCategory);
}

export function normalizeMemoryCategory(value: unknown): MemoryCategory {
  if (typeof value !== 'string') {
    return 'fact';
  }
  const normalized = value.trim().toLowerCase();
  if (isMemoryCategory(normalized)) {
    return normalized;
  }
  return MEMORY_CATEGORY_ALIASES[normalized] ?? 'fact';
}

export function toMemory(payload: MemoryPayloadLike): Memory {
  const text = payload.text ?? payload.content ?? payload.fact_text ?? '';
  const category = normalizeMemoryCategory(
    payload.category ?? payload.memory_type ?? payload.type
  );
  const importance = Number(
    payload.importance ?? payload.salience_score ?? payload.score ?? 0
  );
  const confidence = Number(payload.confidence ?? payload.score ?? 0);
  return {
    id: payload.id ?? payload.memory_id ?? '',
    text,
    category,
    importance: Number.isFinite(importance) ? importance : 0,
    confidence: Number.isFinite(confidence) ? confidence : 0,
    lastAccessed: parseMemoryDate(payload.lastAccessed ?? payload.last_accessed_at),
    createdAt: parseMemoryDate(payload.createdAt ?? payload.created_at),
    embedding: parseMemoryEmbedding(payload.embedding ?? payload.fact_embedding),
  };
}
