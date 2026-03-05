import React from 'react';
import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { Toast, ToastType } from '../contexts/ToastContext';

interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
}

const getToastIcon = (type: ToastType) => {
  switch (type) {
    case 'success':
      return <CheckCircle className="h-5 w-5 text-success" />;
    case 'error':
      return <AlertCircle className="h-5 w-5 text-danger" />;
    case 'warning':
      return <AlertTriangle className="h-5 w-5 text-warning" />;
    case 'info':
      return <Info className="h-5 w-5 text-info" />;
    default:
      return <Info className="h-5 w-5 text-info" />;
  }
};

const getToastStyles = (type: ToastType) => {
  switch (type) {
    case 'success':
      return 'bg-success/10 border-success/40 text-text';
    case 'error':
      return 'bg-danger/10 border-danger/40 text-text';
    case 'warning':
      return 'bg-warning/10 border-warning/40 text-text';
    case 'info':
      return 'bg-info/10 border-info/40 text-text';
    default:
      return 'bg-info/10 border-info/40 text-text';
  }
};

export const ToastItem: React.FC<ToastItemProps> = ({ toast, onRemove }) => {
  const ariaLive = toast.type === 'error' || toast.type === 'warning' ? 'assertive' : 'polite';

  return (
    <div
      className={`flex items-start p-4 rounded-lg border shadow-lg transition-all duration-300 ease-in-out ${getToastStyles(
        toast.type
      )}`}
      role="status"
      aria-live={ariaLive}
      aria-atomic="true"
    >
      <div className="flex-shrink-0" aria-hidden="true">{getToastIcon(toast.type)}</div>
      <div className="ml-3 flex-1">
        <p className="text-sm font-medium">{toast.title}</p>
        {toast.message && <p className="mt-1 text-sm opacity-90">{toast.message}</p>}
      </div>
      <div className="ml-4 flex-shrink-0">
        <button
          onClick={() => onRemove(toast.id)}
          className="inline-flex text-current hover:opacity-75 transition-opacity"
          title="Close notification"
          aria-label="Dismiss notification"
          type="button"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};
