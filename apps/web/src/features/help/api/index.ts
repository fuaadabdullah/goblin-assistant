import { apiClient } from '@/lib/api';
import type { TriageResponse } from '@/lib/api/support';
import { UiError } from '../../../lib/ui-error';
import { getUserMessage } from '../../../lib/error/toast';
export type { SupportMessagePayload } from '../types';
export type { TriageResponse, TriageResult } from '@/lib/api/support';

export const sendSupportMessage = async (message: string): Promise<void> => {
  try {
    await apiClient.sendSupportMessage(message);
  } catch (error) {
    throw new UiError(
      {
        code: 'SUPPORT_MESSAGE_FAILED',
        userMessage: getUserMessage(error),
      },
      error
    );
  }
};

export const triageIssue = async (
  description: string,
  context?: string
): Promise<TriageResponse> => {
  try {
    const response = await apiClient.triageIssue(description, context);
    return response.data;
  } catch (error) {
    throw new UiError(
      {
        code: 'TRIAGE_FAILED',
        userMessage: getUserMessage(error),
      },
      error
    );
  }
};
