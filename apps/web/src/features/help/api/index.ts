import { apiClient } from '@/api';
import { UiError } from '../../../lib/ui-error';
import { supportMethods, type TriageResponse } from '../../../lib/api/support';
export type { SupportMessagePayload } from '../types';
export type { TriageResponse } from '../../../lib/api/support';

export const sendSupportMessage = async (message: string): Promise<void> => {
  try {
    await apiClient.sendSupportMessage(message);
  } catch (error) {
    throw new UiError(
      {
        code: 'SUPPORT_MESSAGE_FAILED',
        userMessage: 'We could not send that message right now.',
      },
      error
    );
  }
};

export const triageIssue = async (
  description: string,
  context?: string,
): Promise<TriageResponse> => {
  try {
    const response = await supportMethods.triageIssue(description, context);
    return response.data;
  } catch (error) {
    throw new UiError(
      {
        code: 'TRIAGE_FAILED',
        userMessage: 'We could not triage that issue right now.',
      },
      error
    );
  }
};
