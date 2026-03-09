import React, { useReducer, useEffect } from 'react';
// CSS is imported globally in _app.tsx
import StreamingView from '@/components/streaming/StreamingView';
import { runtimeClient, runtimeClientDemo } from '@/api';
import type { OrchestrationStep } from '@/types/api';
import {
  initialOrchestrationState,
  orchestrationReducer,
} from '@/lib/orchestration/orchestrationState';
import { useOrchestrationExecution } from '@/lib/orchestration/useOrchestrationExecution';
import { debugLog } from '@/lib/utils/debug';
import { devError } from '@/utils/dev-log';
import { formatCost } from '@/utils/format-cost';

interface Props {
  provider?: string | null | undefined;
  model?: string | null | undefined;
  demoMode?: boolean;
}

const ORCHESTRATION_TEMPLATES = [
  {
    name: 'Document & Test',
    description: 'Document code and write unit tests',
    value: 'docs-writer: document this code THEN code-writer: write a unit test',
  },
  {
    name: 'Analyze & Optimize',
    description: 'Analyze code quality and suggest improvements',
    value: 'code-writer: analyze this code for issues THEN code-writer: suggest optimizations',
  },
  {
    name: 'Review & Refactor',
    description: 'Review code and provide refactoring suggestions',
    value: 'code-writer: review this code THEN code-writer: suggest refactoring',
  },
  {
    name: 'Custom',
    description: 'Write your own orchestration',
    value: '',
  },
];

export default function GoblinDemo({ provider, model, demoMode = false }: Props) {
  // Consolidated state using reducer
  const [state, dispatch] = useReducer(orchestrationReducer, {
    ...initialOrchestrationState,
    codeInput: '// Write code or paste here\nfunction add(a, b) {\n  return a + b;\n}',
    orchestration: 'docs-writer: document this code THEN code-writer: write a unit test',
    selectedTemplate: 'Document & Test',
  });

  // Helper function to get the appropriate runtime client
  const getRuntimeClient = () => (demoMode ? runtimeClientDemo : runtimeClient);

  // Orchestration execution hook
  const { executeOrchestration, streamingTimeoutRef } = useOrchestrationExecution({
    dispatch,
    runtimeClient: getRuntimeClient(),
    provider,
    model,
  });

  useEffect(() => {
    return () => {
      if (streamingTimeoutRef.current) {
        clearTimeout(streamingTimeoutRef.current);
        streamingTimeoutRef.current = null;
      }
    };
  }, [streamingTimeoutRef]);

  useEffect(() => {
    if (state.orchestration.trim()) {
      previewOrchestration();
    } else {
      dispatch({ type: 'SET_PREVIEW_PLAN', payload: null });
      dispatch({ type: 'SET_ESTIMATED_COST', payload: 0 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.orchestration]);

  const previewOrchestration = async () => {
    debugLog('🔍 [DEBUG] Previewing orchestration:', {
      orchestration: state.orchestration,
    });

    const client = getRuntimeClient();
    try {
      const plan = await client.parseOrchestration(state.orchestration, 'demo');
      debugLog('✅ [DEBUG] Preview plan received:', {
        steps: plan.steps.length,
        totalBatches: plan.total_batches,
      });
      dispatch({ type: 'SET_PREVIEW_PLAN', payload: plan });
      // Estimate cost based on steps (rough approximation)
      const estimated = plan.steps.length * 0.02; // $0.02 per step average
      dispatch({ type: 'SET_ESTIMATED_COST', payload: estimated });
    } catch (error) {
      devError('❌ [DEBUG] Failed to preview orchestration:', error);
      dispatch({ type: 'SET_PREVIEW_PLAN', payload: null });
      dispatch({ type: 'SET_ESTIMATED_COST', payload: 0 });
    }
  };

  const handleTemplateChange = (templateName: string) => {
    debugLog('🎯 [DEBUG] Template changed:', { from: state.selectedTemplate, to: templateName });

    dispatch({ type: 'SET_SELECTED_TEMPLATE', payload: templateName });
    const template = ORCHESTRATION_TEMPLATES.find(t => t.name === templateName);
    if (template) {
      debugLog('📝 [DEBUG] Setting orchestration to:', template.value);
      dispatch({ type: 'SET_ORCHESTRATION', payload: template.value });
    }
  };

  const run = async () => {
    await executeOrchestration(state.orchestration, state.codeInput);
  };

  return (
    <div className="goblin-demo" data-testid="goblin-demo">
      <div className="inputs" data-testid="goblin-inputs">
        <label htmlFor="codeInput" data-testid="code-input-label">
          Code
        </label>
        <textarea
          id="codeInput"
          value={state.codeInput}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
            dispatch({ type: 'SET_CODE_INPUT', payload: e.target.value })
          }
          rows={10}
          className="code-input"
          data-testid="code-input"
          aria-describedby="code-input-help"
        />
        <div id="code-input-help" className="sr-only">
          Enter or paste the code you want to process with the orchestration
        </div>

        <label htmlFor="template-select" data-testid="template-select-label">
          Orchestration Template
        </label>
        <select
          id="template-select"
          value={state.selectedTemplate}
          onChange={e => handleTemplateChange(e.target.value)}
          className="template-select"
          data-testid="template-select"
          aria-describedby="template-select-help"
        >
          {ORCHESTRATION_TEMPLATES.map(template => (
            <option
              key={template.name}
              value={template.name}
              data-testid={`template-option-${template.name.replace(/\s+/g, '-').toLowerCase()}`}
            >
              {template.name} - {template.description}
            </option>
          ))}
        </select>
        <div id="template-select-help" className="sr-only">
          Choose a predefined orchestration template or select Custom to write your own
        </div>

        <label htmlFor="orch" data-testid="orchestration-label">
          Orchestration
        </label>
        <input
          id="orch"
          value={state.orchestration}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
            dispatch({ type: 'SET_ORCHESTRATION', payload: e.target.value })
          }
          data-testid="orchestration-input"
          aria-describedby="orchestration-help"
        />
        <div id="orchestration-help" className="sr-only">
          Define the sequence of AI operations to perform on your code
        </div>

        {state.previewPlan && (
          <div
            className="plan-preview"
            data-testid="plan-preview"
            aria-labelledby="plan-preview-title"
            aria-describedby="estimated-cost"
          >
            <h4 id="plan-preview-title" data-testid="plan-preview-title">
              Plan Preview ({state.previewPlan.steps.length} steps)
            </h4>
            <div id="estimated-cost" className="estimated-cost" data-testid="estimated-cost">
              Estimated Cost: {formatCost(state.estimatedCost, { mode: 'per-message' })}
            </div>
            <ul className="plan-steps" data-testid="plan-steps">
              {state.previewPlan.steps.map((step, index) => (
                <li key={step.id} className="plan-step" data-testid={`plan-step-${step.id}`}>
                  <span className="step-number" data-testid={`step-number-${step.id}`}>
                    {index + 1}.
                  </span>
                  <span className="step-goblin" data-testid={`step-goblin-${step.id}`}>
                    {step.goblin}:
                  </span>
                  <span className="step-task" data-testid={`step-task-${step.id}`}>
                    {step.task}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="control-row" data-testid="control-row">
          <button
            disabled={state.running}
            onClick={() => run()}
            data-testid="run-button"
            aria-label={
              state.running
                ? 'Orchestration is currently running'
                : 'Run the orchestration on the provided code'
            }
            aria-describedby="run-button-status"
          >
            {state.running ? 'Running...' : 'Run'}
          </button>
          <div id="run-button-status" className="sr-only">
            {state.running
              ? 'The orchestration is currently executing. Please wait for it to complete.'
              : 'Click to start executing the orchestration steps on your code.'}
          </div>
        </div>
      </div>
      <div
        className="goblin-results"
        data-testid="goblin-results"
      >
        {/* Plan preview */}
        {Object.keys(state.stepCosts).length > 0 && (
          <div className="plan-total" data-testid="plan-total">
            <strong>Total Plan Cost: </strong>
            {formatCost((Object.values(state.stepCosts) as number[]).reduce((a, b) => a + b, 0), {
              mode: 'per-token',
            })}
          </div>
        )}
        {state.plan && (
          <div className="plan-preview" data-testid="execution-plan">
            <h3 data-testid="execution-plan-title">Plan Preview</h3>
            <ol data-testid="execution-steps">
              {state.plan.steps.map((s: OrchestrationStep) => (
                <li
                  key={s.id}
                  onClick={() => dispatch({ type: 'TOGGLE_EXPANDED_STEP', payload: s.id })}
                  className="execution-step"
                  data-testid={`execution-step-${s.id}`}
                >
                  <strong data-testid={`execution-step-goblin-${s.id}`}>{s.goblin}</strong>:{' '}
                  <span data-testid={`execution-step-task-${s.id}`}>{s.task}</span>{' '}
                  <em data-testid={`execution-step-status-${s.id}`}>
                    ({state.stepStatuses[s.id] || 'pending'})
                  </em>{' '}
                  <span className="execution-step-cost" data-testid={`execution-step-cost-${s.id}`}>
                    {(state.stepCosts[s.id] || 0) > 0
                      ? formatCost(state.stepCosts[s.id] || 0, { mode: 'per-token' })
                      : ''}
                  </span>
                  {state.expandedSteps[s.id] && (
                    <div className="step-details" data-testid={`step-details-${s.id}`}>
                      <div data-testid={`step-id-${s.id}`}>Step ID: {s.id}</div>
                      <div data-testid={`step-status-${s.id}`}>Status: {state.stepStatuses[s.id]}</div>
                      <div data-testid={`step-cost-${s.id}`}>
                        Cost: {formatCost(state.stepCosts[s.id] || 0, { mode: 'per-token' })}
                      </div>
                      <div data-testid={`step-tokens-${s.id}`}>Tokens: {state.stepTokens[s.id] || 0}</div>
                      {state.stepChunks[s.id] && state.stepChunks[s.id].length > 0 && (
                        <div className="chunk-list" data-testid={`chunk-list-${s.id}`}>
                          <strong>Chunks:</strong>
                          <ul data-testid={`chunks-${s.id}`}>
                            {state.stepChunks[s.id].map((c, idx) => (
                              <li key={`chunk-${s.id}-${idx}`} data-testid={`chunk-${s.id}-${idx}`}>
                                <span
                                  className="chunk-text"
                                  data-testid={`chunk-text-${s.id}-${idx}`}
                                >
                                  {c.chunk}
                                </span>
                                <span
                                  className="chunk-meta"
                                  data-testid={`chunk-tokens-${s.id}-${idx}`}
                                >
                                  Tokens: {c.token}
                                </span>
                                <span
                                  className="chunk-meta"
                                  data-testid={`chunk-cost-${s.id}-${idx}`}
                                >
                                  Cost: {formatCost(c.cost, { mode: 'per-token' })}
                                </span>
                                <progress
                                  className="chunk-graph"
                                  max={100}
                                  value={Math.min(100, c.cost * 1000)}
                                  data-testid={`chunk-graph-${s.id}-${idx}`}
                                  aria-label={`Cost visualization for chunk ${idx + 1}`}
                                />
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </div>
        )}
        <StreamingView streamingText={state.streamingText} isStreaming={state.isStreaming} />
      </div>
    </div>
  );
}
