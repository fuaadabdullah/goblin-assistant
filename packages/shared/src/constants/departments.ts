/**
 * Department constants — shared between frontend and backend.
 *
 * These are the canonical department IDs and display names.
 * Users see departments, not provider names.
 */
export const DEPARTMENTS = {
  reasoning: {
    id: 'reasoning',
    name: 'Reasoning',
    description: 'Logic, analysis, planning, math, and problem-solving',
  },
  coding: {
    id: 'coding',
    name: 'Coding',
    description: 'Code generation, debugging, refactoring, code review',
  },
  creative: {
    id: 'creative',
    name: 'Creative',
    description: 'Writing, brainstorming, content creation',
  },
  recall: {
    id: 'recall',
    name: 'Recall',
    description: 'Memory retrieval, context assembly, information lookup',
  },
  tool_use: {
    id: 'tool_use',
    name: 'Tools',
    description: 'Function calling, structured actions, automation',
  },
  research: {
    id: 'research',
    name: 'Research',
    description: 'Deep research, multi-source synthesis, investigation',
  },
  general: {
    id: 'general',
    name: 'General',
    description: 'General-purpose assistant for uncategorized requests',
  },
} as const;

export type DepartmentId = keyof typeof DEPARTMENTS;

export interface DepartmentInfo {
  id: DepartmentId;
  name: string;
  description: string;
}

export function getDepartmentInfo(id: string): DepartmentInfo | undefined {
  return (DEPARTMENTS as Record<string, DepartmentInfo | undefined>)[id];
}

export function listDepartments(): DepartmentInfo[] {
  return Object.values(DEPARTMENTS);
}

export function isValidDepartment(id: string): id is DepartmentId {
  return id in DEPARTMENTS;
}