import { render, screen, fireEvent } from '@testing-library/react';

// Mock dependencies
vi.mock('../../components/streaming/StreamingView', () => ({
  default: function MockStreamingView() {
    return <div data-testid="streaming-view" />;
  },
}));
vi.mock('@/lib/api/runtimeClient', () => ({
  runtimeClient: {
    parseOrchestration: vi.fn().mockResolvedValue({ steps: [], total_batches: 0 }),
    executeTaskStreaming: vi.fn(),
    executeTask: vi.fn(),
  },
  runtimeClientDemo: {
    parseOrchestration: vi.fn().mockResolvedValue({ steps: [], total_batches: 0 }),
    executeTaskStreaming: vi.fn(),
    executeTask: vi.fn(),
  },
}));
vi.mock('../../lib/orchestration/orchestrationState', () => {
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
    orchestrationReducer: (
      state: typeof initialState,
      action: { type: string; payload?: unknown }
    ) => {
      switch (action.type) {
        case 'SET_CODE_INPUT':
          return { ...state, codeInput: action.payload };
        case 'SET_ORCHESTRATION':
          return { ...state, orchestration: action.payload };
        default:
          return state;
      }
    },
  };
});
const mockExecuteOrchestration = vi.fn();
vi.mock('../../lib/orchestration/useOrchestrationExecution', () => ({
  useOrchestrationExecution: () => ({
    executeOrchestration: mockExecuteOrchestration,
    streamingTimeoutRef: { current: null },
  }),
}));
vi.mock('../../utils/format-cost', () => ({
  formatCost: (val: number) => `$${val.toFixed(2)}`,
}));
vi.mock('../../lib/utils/debug', () => ({
  debugLog: vi.fn(),
}));
vi.mock('../../utils/dev-log', () => ({
  devError: vi.fn(),
  devWarn: vi.fn(),
  devLog: vi.fn(),
}));

import GoblinDemo from '../GoblinDemo';

describe('GoblinDemo', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the demo page with orchestration input', async () => {
    render(<GoblinDemo />);
    expect(await screen.findByTestId('template-select-label')).toBeInTheDocument();
  });

  it('renders with provider and model props', async () => {
    render(<GoblinDemo provider="openai" model="gpt-4" />);
    expect(await screen.findByTestId('template-select-label')).toBeInTheDocument();
  });

  it('renders in demo mode', async () => {
    render(<GoblinDemo demoMode />);
    expect(await screen.findByTestId('template-select-label')).toBeInTheDocument();
  });

  it('renders code input area', async () => {
    const { container } = render(<GoblinDemo />);
    await screen.findByTestId('template-select-label');
    const textareas = container.querySelectorAll('textarea');
    expect(textareas.length).toBeGreaterThan(0);
  });

  it('allows typing in code input', async () => {
    const { container } = render(<GoblinDemo />);
    await screen.findByTestId('template-select-label');
    const textareas = container.querySelectorAll('textarea');
    if (textareas.length > 0) {
      fireEvent.change(textareas[0], { target: { value: 'print("hello")' } });
    }
  });
});
