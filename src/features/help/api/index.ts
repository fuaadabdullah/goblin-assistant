import { apiClient } from '../../../api/apiClient';
import { UiError } from '../../../lib/ui-error';
export type { SupportMessagePayload } from '../types';

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
