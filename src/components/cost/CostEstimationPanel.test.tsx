import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import CostEstimationPanel, {
  computeLocalCostEstimate,
  formatCost,
  getCostColor,
  getCachedRate,
} from './CostEstimationPanel';
import { runtimeClient } from '@/api/api-client';

vi.mock('@/api/api-client', () => ({
  runtimeClient: {
    estimateCost: vi.fn(),
    estimateCostStream: vi.fn(),
  },
  raptorStatus: vi.fn(),
  raptorStart: vi.fn(),
  raptorStop: vi.fn(),
  raptorLogs: vi.fn(),
}));

const mockedRuntime = vi.mocked(runtimeClient) as any;

describe('CostEstimationPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows placeholder when orchestrationText is empty and calls onEstimatedCostChange(0)', () => {
    const onChange = vi.fn();
    render(<CostEstimationPanel orchestrationText="" onEstimatedCostChange={onChange} />);
    expect(
      screen.getByText(/Enter an orchestration command to see cost estimates/i)
    ).toBeInTheDocument();
    expect(onChange).toHaveBeenCalledWith(0);
  });

  it('renders estimate results when backend returns values and calls backend with correct args and shows rate-limit', async () => {
    const fakeEstimate = {
      totalCost: 0.05,
      stepCosts: [
        {
          stepId: 's1',
          goblin: 'Alpha',
          task: 'Fetch data',
          estimatedCost: 0.02,
          tokenEstimate: 200,
        },
        {
          stepId: 's2',
          goblin: 'Beta',
          task: 'Process data',
          estimatedCost: 0.03,
          tokenEstimate: 300,
        },
      ],
      currency: 'USD',
      rateLimit: { limit: 1000, remaining: 999 },
    };

    mockedRuntime.estimateCost.mockResolvedValueOnce(fakeEstimate);
    const onChange = vi.fn();

    render(
      <CostEstimationPanel orchestrationText="fetch and process" onEstimatedCostChange={onChange} />
    );

    await waitFor(() => {
      expect(screen.getByText(/Total Estimated Cost/i)).toBeInTheDocument();
      expect(screen.getByText('$0.0500')).toBeInTheDocument();
      expect(screen.getByText('Alpha')).toBeInTheDocument();
      expect(screen.getByText('Beta')).toBeInTheDocument();
      // Rate-limit UI shown
      expect(screen.getByText(/API Rate Limit: 999\/1000/i)).toBeInTheDocument();
    });

    expect(onChange).toHaveBeenCalledWith(0.05);
    expect(mockedRuntime.estimateCost).toHaveBeenCalledWith(
      'fetch and process',
      '',
      undefined,
      undefined
    );
  });

  it('falls back to local estimate when backend fails due to missing credentials and shows specific warning', async () => {
    const error = new Error('Missing pricing API credentials');
    mockedRuntime.estimateCost.mockRejectedValueOnce(error);
    const onChange = vi.fn();

    // orchestrationText and code inputs
    render(
      <CostEstimationPanel
        orchestrationText="run"
        codeInput="console.log('hi')"
        provider="openai"
        model="demo"
        onEstimatedCostChange={onChange}
      />
    );

    await waitFor(() => {
      expect(screen.getByText(/Pricing API credentials missing/i)).toBeInTheDocument();
    });

    const local = computeLocalCostEstimate('run', "console.log('hi')", 'openai', 'demo');
    expect(onChange).toHaveBeenCalledWith(local);
    expect(screen.getAllByText(formatCost(local))).toHaveLength(2); // Total cost and step cost
  });

  it('applies cost color classes correctly and truncates long task titles', async () => {
    const longTask = 'This is a very long task name that should be truncated to 30 characters!';

    const fakeEstimate = {
      totalCost: 0.0004,
      stepCosts: [
        {
          stepId: 's1',
          goblin: 'LocalGoblin',
          task: longTask,
          estimatedCost: 0.0002,
          tokenEstimate: 1,
        },
      ],
      currency: 'USD',
    };

    mockedRuntime.estimateCost.mockResolvedValueOnce(fakeEstimate);

    render(<CostEstimationPanel orchestrationText="something small" />);

    await waitFor(() => {
      const totalElem = screen.getByText(formatCost(fakeEstimate.totalCost));
      expect(totalElem).toBeInTheDocument();
      // expect class name includes the correct cost color
      expect(totalElem.className).toContain(getCostColor(fakeEstimate.totalCost));

      // Step task should be truncated
      expect(screen.getByText(/This is a very long task name \.\.\./i)).toBeInTheDocument();
    });
  });

  it('shows streaming output area during streaming and then displays formatted summary and copy button', async () => {
    // Simulate streaming client available on runtimeClient
    const streamChunks = ['Progress 1', 'Progress 2'];

    // Provide a streaming function on runtime client mock
    mockedRuntime.estimateCostStream = vi.fn(
      async (
        _text: string,
        _code: string,
        _provider: string,
        _model: string,
        onChunk: (chunk: string) => void
      ) => {
        for (const c of streamChunks) {
          onChunk(c);
        }
      }
    );

    const fakeEstimate = {
      totalCost: 0.02,
      stepCosts: [
        {
          stepId: 's1',
          goblin: 'StreamGoblin',
          task: 'Stream Task',
          estimatedCost: 0.02,
          tokenEstimate: 100,
        },
      ],
      currency: 'USD',
    };
    mockedRuntime.estimateCost.mockResolvedValueOnce(fakeEstimate);

    render(<CostEstimationPanel orchestrationText="stream test" />);

    // Wait for streaming lines to appear
    await waitFor(() => {
      expect(screen.getByText('Progress 1')).toBeInTheDocument();
      expect(screen.getByText('Progress 2')).toBeInTheDocument();
    });

    // After streaming, the summary should be shown
    await waitFor(() => expect(screen.getByText('Formatted Summary')).toBeInTheDocument());

    // Mock clipboard
    const writeSpy = vi.fn();
    const originalNavigator = (globalThis as { navigator?: { clipboard?: { writeText: unknown } } })
      .navigator;
    (globalThis as { navigator: { clipboard: { writeText: unknown } } }).navigator = {
      clipboard: { writeText: writeSpy },
    };

    const copyButton = screen.getByRole('button', { name: /Copy formatted docs/i });
    copyButton.click();
    expect(writeSpy).toHaveBeenCalled();

    // Copy status should appear in the Badge component, not as a class on the button
    await waitFor(() => {
      expect(screen.getByText(/Copied/i)).toBeInTheDocument();
      // With shadcn/ui Button, the copied state is shown in a Badge, not a class
      expect(copyButton).toBeInTheDocument(); // Button should still exist
    });

    // Cleanup navigator
    if (originalNavigator) {
      (globalThis as any).navigator = originalNavigator;
    }

    // Summary content present
    expect(screen.getByText(/totalCost/i)).toBeInTheDocument();
  });
});

describe('helper functions', () => {
  it('formatCost: formats different ranges correctly', () => {
    expect(formatCost(0.0004)).toBe('$0.40m'); // millicents
    expect(formatCost(0.005)).toBe('$0.0050'); // micro dollars
    expect(formatCost(0.12345)).toBe('$0.1235'); // normal dollars
  });

  it('getCostColor: returns correct classes based on thresholds', () => {
    expect(getCostColor(0.0004)).toBe('cost-low');
    expect(getCostColor(0.005)).toBe('cost-medium');
    expect(getCostColor(0.05)).toBe('cost-high');
    expect(getCostColor(1.2)).toBe('cost-very-high');
  });

  it('computeLocalCostEstimate: respects provider/model cached rates', () => {
    const base = computeLocalCostEstimate('abc', 'def');
    const openai = computeLocalCostEstimate('abc', 'def', 'openai');
    const anthropic = computeLocalCostEstimate('abc', 'def', 'anthropic');

    // Cache values expected to differ by provider
    expect(getCachedRate('openai', 'demo')).toBeGreaterThanOrEqual(0);
    expect(getCachedRate('anthropic', 'demo')).toBeGreaterThanOrEqual(0);

    // anthropic should be >= openai given our rates in RATE_CACHE above
    expect(anthropic).toBeGreaterThanOrEqual(openai);

    // Minimum should be enforced and base should be a number
    expect(base).toBeGreaterThanOrEqual(0.001);

    // Minimum should be enforced
    const min = computeLocalCostEstimate('', '', 'anthropic');
    expect(min).toBeGreaterThanOrEqual(0.001);
  });
});
