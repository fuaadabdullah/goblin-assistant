import type { NextApiRequest, NextApiResponse } from 'next';

type HealthResponse = {
  status: 'ok';
  service: 'goblin-assistant-web';
};

export default function handler(
  _req: NextApiRequest,
  res: NextApiResponse<HealthResponse>,
) {
  res.status(200).json({
    status: 'ok',
    service: 'goblin-assistant-web',
  });
}
