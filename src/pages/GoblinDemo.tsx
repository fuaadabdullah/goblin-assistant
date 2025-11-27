import React, { useState, useEffect } from 'react';
import './GoblinDemo.css';
import StreamingView from '@/components/streaming/StreamingView';
import { runtimeClient, runtimeClientDemo } from '@/api/api-client';
import type {
  OrchestrationPlan,
  OrchestrationStep,
  StreamChunk,
  TaskResponse,
} from '@/api/api-client';

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
  const [codeInput, setCodeInput] = useState<string>(
    '// Write code or paste here\nfunction add(a, b) {\n  return a + b;\n}'
  );
  const [orchestration, setOrchestration] = useState<string>(
    'docs-writer: document this code THEN code-writer: write a unit test'
  );
  const [streamingText, setStreamingText] = useState<string>('');
  const [running, setRunning] = useState<boolean>(false);
  const [plan, setPlan] = useState<OrchestrationPlan | null>(null);
  const [previewPlan, setPreviewPlan] = useState<OrchestrationPlan | null>(null);
  const [estimatedCost, setEstimatedCost] = useState<number>(0);
  const [stepStatuses, setStepStatuses] = useState<Record<string, string>>({});
  const [stepCosts, setStepCosts] = useState<Record<string, number>>({});
  const [stepTokens, setStepTokens] = useState<Record<string, number>>({});
  const [stepChunks, setStepChunks] = useState<
    Record<string, Array<{ chunk: string; token: number; cost: number }>>
  >({});
  const [selectedTemplate, setSelectedTemplate] = useState<string>('Document & Test');
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [streamingTimeout, setStreamingTimeout] = useState<NodeJS.Timeout | null>(null);
  const [fallbackTriggered, setFallbackTriggered] = useState<boolean>(false);

  // Helper function to get the appropriate runtime client
  const getRuntimeClient = () => (demoMode ? runtimeClientDemo : runtimeClient);
  useEffect(() => {
    if (orchestration.trim()) {
      previewOrchestration();
    } else {
      setPreviewPlan(null);
      setEstimatedCost(0);
    }
  }, [orchestration]);

  const previewOrchestration = async () => {
    console.log('🔍 [DEBUG] Previewing orchestration:', {
      orchestration,
      codeInput: codeInput.substring(0, 100) + '...',
    });

    try {
      const client = getRuntimeClient();
      const plan = await client.parseOrchestration(orchestration, codeInput);
      console.log('✅ [DEBUG] Orchestration parsed successfully:', {
        steps: plan.steps.length,
        totalBatches: plan.total_batches,
      });
      setPreviewPlan(plan);
      // Estimate cost based on steps (rough approximation)
      // Estimate cost based on number of steps (rough approximation)
      const estimated = plan.steps.length * 0.02; // $0.02 per step average
      setEstimatedCost(estimated);
    } catch (error) {
      console.error('❌ [DEBUG] Failed to preview orchestration:', error);
      setPreviewPlan(null);
      setEstimatedCost(0);
    }
  };

  const handleTemplateChange = (templateName: string) => {
    console.log('🎯 [DEBUG] Template changed:', { from: selectedTemplate, to: templateName });

    setSelectedTemplate(templateName);
    const template = ORCHESTRATION_TEMPLATES.find(t => t.name === templateName);
    if (template) {
      console.log('📝 [DEBUG] Setting orchestration to:', template.value);
      setOrchestration(template.value);
    }
  };

  const run = async () => {
    console.log('🚀 [DEBUG] Starting execution:', {
      orchestration,
      codeLength: codeInput.length,
      demoMode,
    });

    setStreamingText('');
    setRunning(true);
    setIsStreaming(true);
    setFallbackTriggered(false);

    // Set up streaming timeout for fallback (10 seconds)
    const timeout = setTimeout(() => {
      if (isStreaming && !fallbackTriggered) {
        console.warn('⏰ [DEBUG] Streaming timeout - falling back to non-streaming mode');
        setFallbackTriggered(true);
        setIsStreaming(false);
        fallbackToNonStreaming();
      }
    }, 10000);

    setStreamingTimeout(timeout);

    // Use a fixed goblin id as default for parsing
    const goblin = 'demo';
    setPlan(null);
    setStepStatuses({});
    setStepCosts({});
    setStepTokens({});

    try {
      const client = getRuntimeClient();
      console.log('🔄 [DEBUG] Parsing orchestration...');
      const parsed = await client.parseOrchestration(orchestration, goblin);
      console.log('✅ [DEBUG] Orchestration parsed:', {
        steps: parsed.steps?.length || 0,
        totalBatches: parsed.total_batches,
      });
      setPlan(parsed);

      if (!parsed?.steps || parsed.steps.length === 0) {
        console.warn('⚠️ [DEBUG] No steps to run');
        setStreamingText((s: string) => s + 'No steps to run\n');
        setRunning(false);
        setIsStreaming(false);
        return;
      }

      for (const step of parsed.steps) {
        console.log('🎬 [DEBUG] Executing step:', {
          id: step.id,
          goblin: step.goblin,
          task: step.task.substring(0, 50) + '...',
        });

        setStepStatuses((prev: Record<string, string>) => ({ ...prev, [step.id]: 'running' }));

        try {
          console.log('📡 [DEBUG] Starting streaming execution for step:', step.id);
          await client.executeTaskStreaming(
            step.goblin,
            step.task,
            (chunk: StreamChunk) => {
              console.log('📦 [DEBUG] Received chunk:', {
                stepId: step.id,
                chunkPreview: (chunk.content || JSON.stringify(chunk)).substring(0, 50) + '...',
                tokenCount: chunk.token_count,
                costDelta: chunk.cost_delta,
              });

              // Clear timeout on first chunk received
              if (streamingTimeout) {
                clearTimeout(streamingTimeout);
                setStreamingTimeout(null);
              }

              const chunkText = chunk.content || JSON.stringify(chunk);
              setStreamingText((s: string) => s + chunkText + '\n');
              const tokenCount = (chunk.token_count as number) || (chunk.tokenCount as number) || 0;
              const costDelta = (chunk.cost_delta as number) || (chunk.costDelta as number) || 0;
              if (tokenCount) {
                setStepTokens((prev: Record<string, number>) => ({
                  ...prev,
                  [step.id]: (prev[step.id] || 0) + tokenCount,
                }));
              }
              if (tokenCount || costDelta) {
                setStepChunks(prev => ({
                  ...prev,
                  [step.id]: [
                    ...(prev[step.id] || []),
                    { chunk: chunkText, token: tokenCount, cost: costDelta },
                  ],
                }));
              }
            },
            (final: TaskResponse) => {
              console.log('🏁 [DEBUG] Step completed:', {
                stepId: step.id,
                cost: (final as Record<string, unknown>)?.cost,
                reasoning:
                  String((final as Record<string, unknown>)?.reasoning || '').substring(0, 50) +
                  '...',
              });
              setStreamingText(
                (s: string) =>
                  s + `--- Step ${step.id} COMPLETE ---\n` + JSON.stringify(final) + '\n'
              );
              const c = Number((final as Record<string, unknown>)?.cost) || 0;
              setStepCosts((prev: Record<string, number>) => ({ ...prev, [step.id]: c }));
            },
            codeInput,
            provider || undefined,
            model || undefined
          );

          setStepStatuses((prev: Record<string, string>) => ({ ...prev, [step.id]: 'completed' }));
        } catch (stepError: unknown) {
          console.error(`Step ${step.id} failed:`, stepError);
          setStreamingText(
            (s: string) =>
              s +
              `--- Step ${step.id} FAILED ---\nError: ${stepError instanceof Error ? stepError.message : String(stepError)}\n`
          );

          // If streaming fails, try fallback for this step
          if (!fallbackTriggered) {
            setFallbackTriggered(true);
            setIsStreaming(false);
            await fallbackToNonStreaming();
            break;
          }

          setStepStatuses((prev: Record<string, string>) => ({ ...prev, [step.id]: 'failed' }));
        }
      }
    } catch (err: unknown) {
      console.error('Orchestration failed:', err);
      setStreamingText(
        (s: string) => s + `Error: ${err instanceof Error ? err.message : String(err)}\n`
      );

      // If parsing fails, try non-streaming fallback
      if (!fallbackTriggered) {
        setFallbackTriggered(true);
        setIsStreaming(false);
        await fallbackToNonStreaming();
      }
    } finally {
      setRunning(false);
      setIsStreaming(false);
      if (streamingTimeout) {
        clearTimeout(streamingTimeout);
        setStreamingTimeout(null);
      }
    }
  };

  const fallbackToNonStreaming = async () => {
    try {
      setStreamingText((s: string) => s + '\n--- FALLING BACK TO NON-STREAMING MODE ---\n');

      // Execute without streaming
      const client = getRuntimeClient();
      const result = await client.executeTask(
        'docs-writer', // fallback to docs-writer
        orchestration,
        false, // non-streaming
        codeInput,
        provider || undefined,
        model || undefined
      );

      setStreamingText((s: string) => s + `Fallback result: ${result}\n`);
    } catch (fallbackError: unknown) {
      setStreamingText(
        (s: string) =>
          s +
          `Fallback also failed: ${fallbackError instanceof Error ? fallbackError.message : String(fallbackError)}\n`
      );
    }
  };

  return (
    <div className="goblin-demo" data-testid="goblin-demo">
      <div className="inputs" data-testid="goblin-inputs">
        <label htmlFor="codeInput" data-testid="code-input-label">
          Code
        </label>
        <textarea
          id="codeInput"
          value={codeInput}
          onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setCodeInput(e.target.value)}
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
          value={selectedTemplate}
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
          value={orchestration}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setOrchestration(e.target.value)}
          data-testid="orchestration-input"
          aria-describedby="orchestration-help"
        />
        <div id="orchestration-help" className="sr-only">
          Define the sequence of AI operations to perform on your code
        </div>

        {previewPlan && (
          <div
            className="plan-preview"
            data-testid="plan-preview"
            aria-labelledby="plan-preview-title"
            aria-describedby="estimated-cost"
          >
            <h4 id="plan-preview-title" data-testid="plan-preview-title">
              Plan Preview ({previewPlan.steps.length} steps)
            </h4>
            <div id="estimated-cost" className="estimated-cost" data-testid="estimated-cost">
              Estimated Cost: ${estimatedCost.toFixed(4)}
            </div>
            <ul className="plan-steps" data-testid="plan-steps">
              {previewPlan.steps.map((step, index) => (
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
            disabled={running}
            onClick={() => run()}
            data-testid="run-button"
            aria-label={
              running
                ? 'Orchestration is currently running'
                : 'Run the orchestration on the provided code'
            }
            aria-describedby="run-button-status"
          >
            {running ? 'Running...' : 'Run'}
          </button>
          <div id="run-button-status" className="sr-only">
            {running
              ? 'The orchestration is currently executing. Please wait for it to complete.'
              : 'Click to start executing the orchestration steps on your code.'}
          </div>
        </div>
      </div>
      <div
        style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}
        data-testid="goblin-results"
      >
        {/* Plan preview */}
        {Object.keys(stepCosts).length > 0 && (
          <div className="plan-total" data-testid="plan-total">
            <strong>Total Plan Cost: </strong>
            {`$${(Object.values(stepCosts) as number[]).reduce((a, b) => a + b, 0).toFixed(6)}`}
          </div>
        )}
        {plan && (
          <div className="plan-preview" data-testid="execution-plan">
            <h3 data-testid="execution-plan-title">Plan Preview</h3>
            <ol data-testid="execution-steps">
              {plan.steps.map((s: OrchestrationStep) => (
                <li
                  key={s.id}
                  onClick={() => setExpandedSteps(prev => ({ ...prev, [s.id]: !prev[s.id] }))}
                  style={{ cursor: 'pointer' }}
                  data-testid={`execution-step-${s.id}`}
                >
                  <strong data-testid={`execution-step-goblin-${s.id}`}>{s.goblin}</strong>:{' '}
                  <span data-testid={`execution-step-task-${s.id}`}>{s.task}</span>{' '}
                  <em data-testid={`execution-step-status-${s.id}`}>
                    ({stepStatuses[s.id] || 'pending'})
                  </em>{' '}
                  <span style={{ marginLeft: 12 }} data-testid={`execution-step-cost-${s.id}`}>
                    {(stepCosts[s.id] || 0) > 0 ? `$${(stepCosts[s.id] || 0).toFixed(6)}` : ''}
                  </span>
                  {expandedSteps[s.id] && (
                    <div className="step-details" data-testid={`step-details-${s.id}`}>
                      <div data-testid={`step-id-${s.id}`}>Step ID: {s.id}</div>
                      <div data-testid={`step-status-${s.id}`}>Status: {stepStatuses[s.id]}</div>
                      <div data-testid={`step-cost-${s.id}`}>
                        Cost: ${(stepCosts[s.id] || 0).toFixed(6)}
                      </div>
                      <div data-testid={`step-tokens-${s.id}`}>Tokens: {stepTokens[s.id] || 0}</div>
                      {stepChunks[s.id] && stepChunks[s.id].length > 0 && (
                        <div className="chunk-list" data-testid={`chunk-list-${s.id}`}>
                          <strong>Chunks:</strong>
                          <ul data-testid={`chunks-${s.id}`}>
                            {stepChunks[s.id].map((c, idx) => (
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
                                  Cost: ${c.cost.toFixed(6)}
                                </span>
                                <div
                                  className="chunk-graph"
                                  style={{ ['--w' as string]: `${Math.min(100, c.cost * 1000)}%` }}
                                  data-testid={`chunk-graph-${s.id}-${idx}`}
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
        <StreamingView streamingText={streamingText} isStreaming={isStreaming} />
      </div>
    </div>
  );
}
