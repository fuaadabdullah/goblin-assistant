/**
 * Types for orchestration state management in GoblinDemo
 */

import type { OrchestrationPlan } from '@/types/api';

export interface ChunkData {
  chunk: string;
  token: number;
  cost: number;
}

export interface OrchestrationState {
  codeInput: string;
  orchestration: string;
  streamingText: string;
  running: boolean;
  plan: OrchestrationPlan | null;
  previewPlan: OrchestrationPlan | null;
  estimatedCost: number;
  stepStatuses: Record<string, string>;
  stepCosts: Record<string, number>;
  stepTokens: Record<string, number>;
  stepChunks: Record<string, ChunkData[]>;
  selectedTemplate: string;
  expandedSteps: Record<string, boolean>;
  isStreaming: boolean;
  fallbackTriggered: boolean;
}

export type OrchestrationAction =
  | { type:  'SET_CODE_INPUT'; payload: string }
  | { type: 'SET_ORCHESTRATION'; payload: string }
  | { type: 'SET_STREAMING_TEXT'; payload: string | ((prev: string) => string) }
  | { type: 'SET_RUNNING'; payload: boolean }
  | { type: 'SET_PLAN'; payload: OrchestrationPlan | null }
  | { type: 'SET_PREVIEW_PLAN'; payload: OrchestrationPlan | null }
  | { type: 'SET_ESTIMATED_COST'; payload: number }
  | { type: 'SET_STEP_STATUS'; payload: { stepId: string; status: string } }
  | { type: 'SET_STEP_COSTS'; payload: Record<string, number> }
  | { type: 'SET_STEP_COST'; payload: { stepId: string; cost: number } }
  | { type: 'SET_STEP_TOKENS'; payload: { stepId: string; tokens: number } }
  | { type: 'ADD_STEP_CHUNK'; payload: { stepId: string; chunk: ChunkData } }
  | { type: 'SET_SELECTED_TEMPLATE'; payload: string }
  | { type: 'TOGGLE_EXPANDED_STEP'; payload: string }
  | { type: 'SET_IS_STREAMING'; payload: boolean }
  | { type: 'SET_FALLBACK_TRIGGERED'; payload: boolean }
  | { type: 'RESET_EXECUTION' };

export const initialOrchestrationState: OrchestrationState = {
  codeInput: '// Write code or paste here\nfunction add(a, b) {\n  return a + b;\n}',
  orchestration: 'docs-writer: document this code THEN code-writer: write a unit test',
  streamingText: '',
  running: false,
  plan: null,
  previewPlan: null,
  estimatedCost: 0,
  stepStatuses: {},
  stepCosts: {},
  stepTokens: {},
  stepChunks: {},
  selectedTemplate: 'Document & Test',
  expandedSteps: {},
  isStreaming: false,
  fallbackTriggered: false,
};

// eslint-disable-next-line complexity
export function orchestrationReducer(
  state: OrchestrationState,
  action: OrchestrationAction
): OrchestrationState {
  switch (action.type) {
    case 'SET_CODE_INPUT':
      return { ...state, codeInput: action.payload };
    case 'SET_ORCHESTRATION':
      return { ...state, orchestration: action.payload };
    case 'SET_STREAMING_TEXT':
      return {
        ...state,
        streamingText:
          typeof action.payload === 'function' ? action.payload(state.streamingText) : action.payload,
      };
    case 'SET_RUNNING':
      return { ...state, running: action.payload };
    case 'SET_PLAN':
      return { ...state, plan: action.payload };
    case 'SET_PREVIEW_PLAN':
      return { ...state, previewPlan: action.payload };
    case 'SET_ESTIMATED_COST':
      return { ...state, estimatedCost: action.payload };
    case 'SET_STEP_STATUS':
      return {
        ...state,
        stepStatuses: { ...state.stepStatuses, [action.payload.stepId]: action.payload.status },
      };
    case 'SET_STEP_COSTS':
      return { ...state, stepCosts: action.payload };
    case 'SET_STEP_COST':
      return {
        ...state,
        stepCosts: { ...state.stepCosts, [action.payload.stepId]: action.payload.cost },
      };
    case 'SET_STEP_TOKENS':
      return {
        ...state,
        stepTokens: {
          ...state.stepTokens,
          [action.payload.stepId]:
            (state.stepTokens[action.payload.stepId] || 0) + action.payload.tokens,
        },
      };
    case 'ADD_STEP_CHUNK':
      return {
        ...state,
        stepChunks: {
          ...state.stepChunks,
          [action.payload.stepId]: [
            ...(state.stepChunks[action.payload.stepId] || []),
            action.payload.chunk,
          ],
        },
      };
    case 'SET_SELECTED_TEMPLATE':
      return { ...state, selectedTemplate: action.payload };
    case 'TOGGLE_EXPANDED_STEP':
      return {
        ...state,
        expandedSteps: { ...state.expandedSteps, [action.payload]: !state.expandedSteps[action.payload] },
      };
    case 'SET_IS_STREAMING':
      return { ...state, isStreaming: action.payload };
    case 'SET_FALLBACK_TRIGGERED':
      return { ...state, fallbackTriggered: action.payload };
    case 'RESET_EXECUTION':
      return {
        ...state,
        streamingText: '',
        running: false,
        plan: null,
        stepStatuses: {},
        stepCosts: {},
        stepTokens: {},
        stepChunks: {},
        isStreaming: false,
        fallbackTriggered: false,
      };
    default:
      return state;
  }
}
