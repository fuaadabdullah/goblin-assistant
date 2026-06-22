import { describe, expect, it, vi, beforeEach } from 'vitest';
import { apiClient } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  apiClient: {
    sendSupportMessage: vi.fn(),
    triageIssue: vi.fn(),
  },
}));

import { sendSupportMessage, triageIssue } from '../index';

describe('help api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('preserves backend support errors when available', async () => {
    vi.mocked(apiClient.sendSupportMessage).mockRejectedValueOnce(new Error('Support inbox unavailable'));

    await expect(sendSupportMessage('hello')).rejects.toMatchObject({
      code: 'SUPPORT_MESSAGE_FAILED',
      userMessage: 'Support inbox unavailable',
    });
  });

  it('preserves network error messages for triage failures', async () => {
    vi.mocked(apiClient.triageIssue).mockRejectedValueOnce(new Error('Network Error'));

    await expect(triageIssue('broken')).rejects.toMatchObject({
      code: 'TRIAGE_FAILED',
      userMessage: 'Network Error',
    });
  });

  it('preserves non-Error support failures', async () => {
    vi.mocked(apiClient.sendSupportMessage).mockRejectedValueOnce('support api unavailable');

    await expect(sendSupportMessage('hello')).rejects.toMatchObject({
      code: 'SUPPORT_MESSAGE_FAILED',
      userMessage: 'support api unavailable',
    });
  });
});
