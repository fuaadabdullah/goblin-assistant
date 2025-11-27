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
      return <CheckCircle className="h-5 w-5 text-green-500" />;
    case 'error':
      return <AlertCircle className="h-5 w-5 text-red-500" />;
    case 'warning':
      return <AlertTriangle className="h-5 w-5 text-yellow-500" />;
    case 'info':
      return <Info className="h-5 w-5 text-blue-500" />;
    default:
      return <Info className="h-5 w-5 text-blue-500" />;
  }
};

const getToastStyles = (type: ToastType) => {
  switch (type) {
    case 'success':
      return 'bg-green-50 border-green-200 text-green-800';
    case 'error':
      return 'bg-red-50 border-red-200 text-red-800';
    case 'warning':
      return 'bg-yellow-50 border-yellow-200 text-yellow-800';
    case 'info':
      return 'bg-blue-50 border-blue-200 text-blue-800';
    default:
      return 'bg-blue-50 border-blue-200 text-blue-800';
  }
};

export const ToastItem: React.FC<ToastItemProps> = ({ toast, onRemove }) => {
  return (
    <div
      className={`flex items-start p-4 rounded-lg border shadow-lg transition-all duration-300 ease-in-out ${getToastStyles(
        toast.type
      )}`}
    >
      <div className="flex-shrink-0">{getToastIcon(toast.type)}</div>
      <div className="ml-3 flex-1">
        <p className="text-sm font-medium">{toast.title}</p>
        {toast.message && <p className="mt-1 text-sm opacity-90">{toast.message}</p>}
      </div>
      <div className="ml-4 flex-shrink-0">
        <button
          onClick={() => onRemove(toast.id)}
          className="inline-flex text-current hover:opacity-75 transition-opacity"
          title="Close notification"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};
