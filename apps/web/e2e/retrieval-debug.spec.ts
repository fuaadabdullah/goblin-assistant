import { expect, test } from '@playwright/test';

const trace = {
  request_id: 'req-rag-123',
  user_id: 'user-7',
  timestamp: '2026-09-23T10:00:00Z',
  model_selected: 'gpt-4o-mini',
  token_budget: 1000,
  total_tokens_used: 128,
  items_retrieved: [
    {
      source: 'semantic_retrieval',
      source_id: 'chunk-42',
      content: 'The retrieved passage used to ground the answer.',
      relevance_score: 0.917,
      token_count: 128,
      rank: 1,
      truncated: false,
      metadata: { document: 'handbook.md' },
    },
  ],
  tier_breakdown: {},
  context_hash: 'sha256:example',
  context_snapshot: 'The retrieved passage used to ground the answer.',
  retrieval_time_ms: 24.5,
  truncation_events: [],
  error: null,
};

test('operator can inspect the chunks selected for a retrieval', async ({ page }) => {
  await page.context().addCookies([
    { name: 'goblin_e2e_auth', value: '1', domain: 'localhost', path: '/' },
    { name: 'goblin_e2e_admin', value: '1', domain: 'localhost', path: '/' },
  ]);
  await page.route('**/api/v1/debug/retrieval/history?limit=50', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        traces: [trace],
        summary: {
          total_traces: 1,
          avg_retrieval_time: 24.5,
          avg_tokens_used: 128,
          error_count: 0,
          truncation_count: 0,
        },
      }),
    });
  });

  await page.goto('/debug/retrieval');

  await expect(page.getByRole('heading', { name: 'Retrieval debugger' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'req-rag-123' })).toBeVisible();
  await expect(page.getByText('The retrieved passage used to ground the answer.')).toBeVisible();
  await expect(page.getByText('score 0.917')).toBeVisible();
  await expect(page.getByText('128 / 1000 (13%)')).toBeVisible();
});
