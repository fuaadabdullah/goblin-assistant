import { renderToString } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import CostPanel from '@/components/cost/CostPanel';

const sample = {
  total_cost: 0.123456,
  cost_by_provider: { ollama: 0.0, openai: 0.123456 },
  cost_by_model: { 'gpt-4': 0.12, 'qwen-3': 0.003456 },
};

describe('CostPanel (server render)', () => {
  it('renders cost summary', () => {
    const html = renderToString(<CostPanel costSummary={sample} />);
    expect(html).toContain('Total:');
    expect(html).toContain('openai');
    expect(html).toContain('gpt-4');
  });
});
