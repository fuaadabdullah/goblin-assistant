import type { NextApiRequest, NextApiResponse } from 'next';

// Simple demo endpoint for local development. Returns basic health for models, routing, and sandbox.

export default function handler(_req: NextApiRequest, res: NextApiResponse) {
  const now = new Date().toISOString();

  // For demo purposes, occasionally return degraded state
  const rand = Math.random();
  const models = rand > 0.95 ? 'degraded' : 'ok';
  const routing = rand > 0.98 ? 'down' : 'ok';
  const sandbox = rand > 0.9 ? 'degraded' : 'ok';

  res.status(200).json({ models, routing, sandbox, updatedAt: now });
}
