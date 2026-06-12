export type { Toast, ToastType } from '../store/uiStore';

import { useUIStore } from '../store/uiStore';

export const useToast = () => {
  const toasts = useUIStore((s) => s.toasts);
  const addToast = useUIStore((s) => s.addToast);
  const removeToast = useUIStore((s) => s.removeToast);
  const showSuccess = useUIStore((s) => s.showSuccess);
  const showError = useUIStore((s) => s.showError);
  const showWarning = useUIStore((s) => s.showWarning);
  const showInfo = useUIStore((s) => s.showInfo);

  return { toasts, addToast, removeToast, showSuccess, showError, showWarning, showInfo };
};
