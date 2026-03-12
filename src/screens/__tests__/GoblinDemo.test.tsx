import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

// Mock dependencies
jest.mock('../../components/streaming/StreamingView', () => {
  return function MockStreamingView() {
    return <div data-testid="streaming-view" />;
  };
});
jest.mock('../../api', () => ({
  runtimeClient: { parseOrchestration: jest.fn(), executeTaskStreaming: jest.fn(), executeTask: jest.fn() },
  runtimeClientDemo: { parseOrchestration: jest.fn(), executeTaskStreaming: jest.fn(), executeTask: jest.fn() },
}));
jest.mock('../../lib/orchestration/orchestrationState', () => {
  const initialState = {
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
  return {
    initialOrchestrationState: initialState,
    orchestrationReducer: (state: typeof initialState, action: { type: string; payload?: unknown }) => {
      switch (action.type) {
        case 'SET_CODE_INPUT': return { ...state, codeInput: action.payload };
        case 'SET_ORCHESTRATION': return { ...state, orchestration: action.payload };
        default: return state;
      }
    },
  };
});
const mockExecuteOrchestration = jest.fn();
jest.mock('../../lib/orchestration/useOrchestrationExecution', () => ({
  useOrchestrationExecution: () => ({
    executeOrchestration: mockExecuteOrchestration,
    streamingTimeoutRef: { current: null },
  }),
}));
jest.mock('../../utils/format-cost', () => ({
  formatCost: (val: number) => `$${val.toFixed(2)}`,
}));
jest.mock('../../lib/utils/debug', () => ({
  debugLog: jest.fn(),
}));
jest.mock('../../utils/dev-log', () => ({
  devError: jest.fn(),
}));

import GoblinDemo from '../GoblinDemo';

describe('GoblinDemo', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders the demo page with orchestration input', () => {
    render(<GoblinDemo />);
    expect(screen.getByTestId('template-select-label')).toBeInTheDocument();
  });

  it('renders with provider and model props', () => {
    render(<GoblinDemo provider="openai" model="gpt-4" />);
    expect(screen.getByTestId('template-select-label')).toBeInTheDocument();
  });

  it('renders in demo mode', () => {
    render(<GoblinDemo demoMode />);
    expect(screen.getByTestId('template-select-label')).toBeInTheDocument();
  });

  it('renders code input area', () => {
    const { container } = render(<GoblinDemo />);
    const textareas = container.querySelectorAll('textarea');
    expect(textareas.length).toBeGreaterThan(0);
  });

  it('allows typing in code input', () => {
    const { container } = render(<GoblinDemo />);
    const textareas = container.querySelectorAll('textarea');
    if (textareas.length > 0) {
      fireEvent.change(textareas[0], { target: { value: 'print("hello")' } });
    }
  });
});
