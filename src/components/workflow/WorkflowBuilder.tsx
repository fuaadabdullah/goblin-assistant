import { useState, useEffect } from 'react';
import './WorkflowBuilder.css';

interface WorkflowStep {
  id: string;
  goblin: string;
  task: string;
  condition?: 'THEN' | 'AND' | 'IF_SUCCESS' | 'IF_FAILURE';
}

interface Props {
  onOrchestrationChange: (orchestration: string) => void;
  initialOrchestration?: string;
}

const AVAILABLE_GOBLINS = [
  {
    id: 'docs-writer',
    name: 'Documentation Writer',
    description: 'Documents code and writes comments',
  },
  { id: 'code-writer', name: 'Code Writer', description: 'Writes and refactors code' },
  { id: 'analyze', name: 'Analyzer', description: 'Analyzes code quality and patterns' },
  { id: 'chat', name: 'Chat Assistant', description: 'General conversation and Q&A' },
  { id: 'translate', name: 'Translator', description: 'Language translation tasks' },
  { id: 'summarize', name: 'Summarizer', description: 'Text summarization and condensation' },
];

const CONDITION_TYPES = [
  {
    value: 'THEN',
    label: 'Then (Sequential)',
    description: 'Execute next step after this completes',
  },
  {
    value: 'AND',
    label: 'And (Parallel)',
    description: 'Execute simultaneously with previous step',
  },
  {
    value: 'IF_SUCCESS',
    label: 'If Success',
    description: 'Execute only if previous step succeeds',
  },
  { value: 'IF_FAILURE', label: 'If Failure', description: 'Execute only if previous step fails' },
];

export default function WorkflowBuilder({
  onOrchestrationChange,
  initialOrchestration = '',
}: Props) {
  const [steps, setSteps] = useState<WorkflowStep[]>([]);
  const [selectedGoblin, setSelectedGoblin] = useState<string>('');
  const [taskInput, setTaskInput] = useState<string>('');
  const [isBuilderMode, setIsBuilderMode] = useState<boolean>(false);

  // Parse initial orchestration if provided
  useEffect(() => {
    if (initialOrchestration && !isBuilderMode) {
      // Try to parse the orchestration string into steps
      parseOrchestrationToSteps(initialOrchestration);
    }
  }, [initialOrchestration]);

  // Update orchestration string when steps change
  useEffect(() => {
    const orchestration = buildOrchestrationFromSteps();
    onOrchestrationChange(orchestration);
  }, [steps]);

  const parseOrchestrationToSteps = (orchestration: string) => {
    // Simple parser for existing orchestration syntax
    const parts = orchestration.split(/\s+(THEN|AND|IF_SUCCESS|IF_FAILURE)\s+/i);
    const parsedSteps: WorkflowStep[] = [];

    for (let i = 0; i < parts.length; i += 2) {
      const taskPart = parts[i].trim();
      const condition = i > 0 ? (parts[i - 1] as WorkflowStep['condition']) : undefined;

      // Parse goblin:task format
      const goblinMatch = taskPart.match(/^(\w+):\s*(.+)$/);
      if (goblinMatch) {
        parsedSteps.push({
          id: `step-${parsedSteps.length + 1}`,
          goblin: goblinMatch[1],
          task: goblinMatch[2],
          condition,
        });
      } else {
        // Default goblin for tasks without explicit goblin
        parsedSteps.push({
          id: `step-${parsedSteps.length + 1}`,
          goblin: 'code-writer',
          task: taskPart,
          condition,
        });
      }
    }

    setSteps(parsedSteps);
  };

  const buildOrchestrationFromSteps = (): string => {
    if (steps.length === 0) return '';

    let result = '';
    steps.forEach((step, index) => {
      if (index > 0 && step.condition) {
        result += ` ${step.condition} `;
      }
      result += `${step.goblin}: ${step.task}`;
    });

    return result;
  };

  const addStep = () => {
    if (!selectedGoblin || !taskInput.trim()) return;

    const newStep: WorkflowStep = {
      id: `step-${Date.now()}`,
      goblin: selectedGoblin,
      task: taskInput.trim(),
      condition: steps.length > 0 ? 'THEN' : undefined,
    };

    setSteps([...steps, newStep]);
    setTaskInput('');
  };

  const removeStep = (stepId: string) => {
    setSteps(steps.filter(step => step.id !== stepId));
  };

  const updateStepCondition = (stepId: string, condition: WorkflowStep['condition']) => {
    setSteps(steps.map(step => (step.id === stepId ? { ...step, condition } : step)));
  };

  const moveStep = (fromIndex: number, toIndex: number) => {
    const newSteps = [...steps];
    const [movedStep] = newSteps.splice(fromIndex, 1);
    newSteps.splice(toIndex, 0, movedStep);
    setSteps(newSteps);
  };

  const toggleBuilderMode = () => {
    setIsBuilderMode(!isBuilderMode);
    if (!isBuilderMode) {
      // Switching to builder mode - parse current orchestration
      parseOrchestrationToSteps(initialOrchestration);
    }
  };

  return (
    <div className="workflow-builder">
      <div className="builder-header">
        <h3>Workflow Builder</h3>
        <button
          onClick={toggleBuilderMode}
          className={`mode-toggle ${isBuilderMode ? 'active' : ''}`}
        >
          {isBuilderMode ? 'Text Mode' : 'Visual Builder'}
        </button>
      </div>

      {isBuilderMode ? (
        <div className="visual-builder">
          <div className="step-adder">
            <select
              value={selectedGoblin}
              onChange={e => setSelectedGoblin(e.target.value)}
              className="goblin-select"
              aria-label="Select goblin for workflow step"
            >
              <option value="">Select Goblin</option>
              {AVAILABLE_GOBLINS.map(goblin => (
                <option key={goblin.id} value={goblin.id}>
                  {goblin.name}
                </option>
              ))}
            </select>

            <input
              type="text"
              value={taskInput}
              onChange={e => setTaskInput(e.target.value)}
              placeholder="Enter task description..."
              className="task-input"
              onKeyPress={e => e.key === 'Enter' && addStep()}
            />

            <button
              onClick={addStep}
              className="add-step-btn"
              disabled={!selectedGoblin || !taskInput.trim()}
            >
              Add Step
            </button>
          </div>

          <div className="steps-list">
            {steps.map((step, index) => (
              <div key={step.id} className="step-item">
                <div className="step-controls">
                  <button
                    onClick={() => removeStep(step.id)}
                    className="remove-step-btn"
                    title="Remove step"
                  >
                    ×
                  </button>

                  {index > 0 && (
                    <>
                      <button
                        onClick={() => moveStep(index, index - 1)}
                        className="move-step-btn"
                        title="Move up"
                        disabled={index === 0}
                      >
                        ↑
                      </button>
                      <button
                        onClick={() => moveStep(index, index + 1)}
                        className="move-step-btn"
                        title="Move down"
                        disabled={index === steps.length - 1}
                      >
                        ↓
                      </button>
                    </>
                  )}
                </div>

                <div className="step-content">
                  {index > 0 && (
                    <select
                      value={step.condition || 'THEN'}
                      onChange={e =>
                        updateStepCondition(step.id, e.target.value as WorkflowStep['condition'])
                      }
                      className="condition-select"
                      aria-label={`Select condition for step ${index + 1}`}
                    >
                      {CONDITION_TYPES.map(condition => (
                        <option key={condition.value} value={condition.value}>
                          {condition.label}
                        </option>
                      ))}
                    </select>
                  )}

                  <div className="step-details">
                    <strong>
                      {AVAILABLE_GOBLINS.find(g => g.id === step.goblin)?.name || step.goblin}
                    </strong>
                    <span className="step-task">{step.task}</span>
                  </div>
                </div>
              </div>
            ))}

            {steps.length === 0 && (
              <div className="empty-state">
                <p>No steps added yet. Select a goblin and enter a task to get started.</p>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="text-mode">
          <p>
            Switch to Visual Builder to create workflows step-by-step, or edit the orchestration
            text directly.
          </p>
        </div>
      )}

      <div className="orchestration-output">
        <label>Generated Orchestration:</label>
        <code className="orchestration-text">
          {buildOrchestrationFromSteps() || 'No steps configured'}
        </code>
      </div>
    </div>
  );
}
