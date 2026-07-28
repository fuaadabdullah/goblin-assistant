import type { DepartmentId } from './departments';

export interface ProductExperience {
  id: string;
  name: string;
  departmentId: DepartmentId;
  description: string;
  surfaceTitle: string;
  surfaceBody: string;
  starterPrompt: string;
  icon: string;
  featured: boolean;
}

export const PRODUCTS = {
  research: {
    id: 'research',
    name: 'Research Goblin',
    departmentId: 'research',
    description: 'Turns open questions into sourced briefs, summaries, and deep dives.',
    surfaceTitle: 'Research briefs',
    surfaceBody: 'Turn a topic into citations, synthesis, and next-step follow-ups.',
    starterPrompt:
      'Create a concise research brief on the current state of AI regulation in the US with sources.',
    icon: '🔎',
    featured: true,
  },
  coding: {
    id: 'coding',
    name: 'Coding Goblin',
    departmentId: 'coding',
    description: 'Ships code, fixes bugs, and tightens implementation details.',
    surfaceTitle: 'Code delivery',
    surfaceBody: 'Debug, refactor, review, and ship with fewer dead ends.',
    starterPrompt: 'Debug this Python code and show me the fix with a brief explanation.',
    icon: '⚙️',
    featured: true,
  },
  finance: {
    id: 'finance',
    name: 'Finance Goblin',
    departmentId: 'reasoning',
    description: 'Handles valuation, analysis, and decision support for money questions.',
    surfaceTitle: 'Finance analysis',
    surfaceBody: 'Model the tradeoffs, compare scenarios, and flag the risks.',
    starterPrompt:
      'Analyze AAPL earnings, valuation, and analyst sentiment. Keep it concise and decision-ready.',
    icon: '📈',
    featured: true,
  },
  strategy: {
    id: 'strategy',
    name: 'Strategy Goblin',
    departmentId: 'reasoning',
    description: 'Turns messy goals into plans, tradeoffs, and priorities.',
    surfaceTitle: 'Strategy notes',
    surfaceBody: 'Break the objective into options, constraints, and a recommended path.',
    starterPrompt:
      'Build a strategy memo for launching a new AI feature next quarter. Focus on tradeoffs and risks.',
    icon: '🎯',
    featured: true,
  },
  operations: {
    id: 'operations',
    name: 'Operations Goblin',
    departmentId: 'tool_use',
    description: 'Builds repeatable workflows, structured actions, and execution plans.',
    surfaceTitle: 'Operations flow',
    surfaceBody: 'Automate the repeatable stuff and keep the process moving.',
    starterPrompt:
      'Design an operations workflow for handling customer escalations from intake to resolution.',
    icon: '🧩',
    featured: true,
  },
  general: {
    id: 'general',
    name: 'General Goblin',
    departmentId: 'general',
    description: 'Handles broad requests that do not need a narrower product experience.',
    surfaceTitle: 'General help',
    surfaceBody: 'Use this when the request spans several outcomes or needs a broad first pass.',
    starterPrompt: 'Help me think through a complex request and suggest the best next step.',
    icon: '✨',
    featured: false,
  },
} as const satisfies Record<string, ProductExperience>;

export type ProductId = keyof typeof PRODUCTS;

export function getProductInfo(id: string): ProductExperience | undefined {
  return (PRODUCTS as Record<string, ProductExperience | undefined>)[id];
}

export function listProducts(): ProductExperience[] {
  return Object.values(PRODUCTS);
}

export function listFeaturedProducts(): ProductExperience[] {
  return listProducts().filter((product) => product.featured);
}

export function isValidProduct(id: string): id is ProductId {
  return id in PRODUCTS;
}

export function getProductForDepartment(departmentId: DepartmentId): ProductExperience | undefined {
  return listProducts().find((product) => product.departmentId === departmentId);
}
