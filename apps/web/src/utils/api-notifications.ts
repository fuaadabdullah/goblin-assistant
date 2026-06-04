import { AxiosInstance, AxiosError } from 'axios';
import { useUIStore } from '../store/uiStore';
import { extractApiErrorMessage } from '../lib/api/shared';

/**
 * Interface for custom request metadata to control notification behavior
 */
export interface ApiNotificationMeta {
  successMessage?: string;
  successTitle?: string;
  errorTitle?: string;
  skipGlobalError?: boolean;
}

/**
 * Sets up global toast notification triggers for an Axios API client.
 * This allows the API layer to trigger toasts without needing access to React hooks.
 */
export function setupApiNotifications(apiClient: AxiosInstance) {
  apiClient.interceptors.response.use(
    (response) => {
      const meta = (response.config as any).meta as ApiNotificationMeta | undefined;
      if (meta?.successMessage) {
        useUIStore.getState().addNotification({
          type: 'success',
          title: meta.successTitle || 'Success',
          message: meta.successMessage,
        });
      }
      return response;
    },
    (error: AxiosError<any>) => {
      const meta = (error.config as any)?.meta as ApiNotificationMeta | undefined;
      if (!meta?.skipGlobalError) {
        const message = extractApiErrorMessage(
          error.response?.data,
          error.message || 'An unexpected error occurred'
        );
        useUIStore.getState().addNotification({
          type: 'error',
          title: meta?.errorTitle || 'API Error',
          message,
        });
      }
      return Promise.reject(error);
    }
  );
}
