import { create } from 'zustand';
import {
  applyThemePreset,
  enableHighContrast,
  getCurrentThemePreset,
  getHighContrastPreference,
} from '../theme/theme';
import { devWarn } from '../utils/dev-log';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
}

interface UIState {
  // Theme state
  highContrast: boolean;
  currentTheme: 'default' | 'nocturne' | 'ember';

  // UI state
  sidebarOpen: boolean;
  // Mobile navigation drawer
  mobileNavOpen: boolean;
  chatSidebarOpen: boolean;
  chatPreviewOpen: boolean;
  activeModal: string | null;
  toasts: Toast[];

  // Actions
  setHighContrast: (enabled: boolean) => void;
  setTheme: (theme: 'default' | 'nocturne' | 'ember') => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleMobileNav: () => void;
  setMobileNavOpen: (open: boolean) => void;
  toggleChatSidebar: () => void;
  toggleChatPreview: () => void;
  setChatPreviewOpen: (open: boolean) => void;
  setChatSidebarOpen: (open: boolean) => void;
  openModal: (modalId: string) => void;
  closeModal: () => void;
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  showSuccess: (title: string, message?: string) => void;
  showError: (title: string, message?: string) => void;
  showWarning: (title: string, message?: string) => void;
  showInfo: (title: string, message?: string) => void;
}

let toastCounter = 0;
const generateToastId = (): string => {
  toastCounter += 1;
  return `toast-${toastCounter}-${Date.now()}`;
};

const toastTimeouts = new Map<string, ReturnType<typeof setTimeout>>();

// Helper to load persisted theme preference
const _getPersistedTheme = (): 'default' | 'nocturne' | 'ember' => {
  const persisted = getCurrentThemePreset();
  return persisted === 'nocturne' || persisted === 'ember' || persisted === 'default'
    ? persisted
    : 'default';
};

export const useUIStore = create<UIState>((set, get) => ({
  // Initial state
  highContrast: getHighContrastPreference(),
  currentTheme: _getPersistedTheme(),
  sidebarOpen: true,
  mobileNavOpen: false,
  chatSidebarOpen: false,
  // Preview drawer open (mobile)
  chatPreviewOpen: false,
  activeModal: null,
  toasts: [],

  // Theme actions
  setHighContrast: (enabled: boolean) => {
    enableHighContrast(enabled);
    set({ highContrast: enabled });
  },

  setTheme: (theme: 'default' | 'nocturne' | 'ember') => {
    applyThemePreset(theme);
    set({ currentTheme: theme });
    // Apply theme to document root
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    // Also update via CSS class for broader compatibility
    root.classList.remove('theme-default', 'theme-nocturne', 'theme-ember');
    root.classList.add(`theme-${theme}`);
  },

  // Sidebar actions
  toggleSidebar: () => {
    set((state) => ({ sidebarOpen: !state.sidebarOpen }));
  },

  setSidebarOpen: (open: boolean) => {
    set({ sidebarOpen: open });
  },

  // Mobile navigation actions
  toggleMobileNav: () => {
    set((state) => ({ mobileNavOpen: !state.mobileNavOpen }));
  },

  setMobileNavOpen: (open: boolean) => {
    set({ mobileNavOpen: open });
  },

  toggleChatSidebar: () => {
    set((state) => ({
      chatSidebarOpen: !state.chatSidebarOpen,
    }));
  },

  toggleChatPreview: () => {
    set((state) => ({ chatPreviewOpen: !state.chatPreviewOpen }));
  },

  setChatPreviewOpen: (open: boolean) => {
    set({ chatPreviewOpen: open });
  },

  setChatSidebarOpen: (open: boolean) => {
    set({ chatSidebarOpen: open });
  },

  // Modal actions
  openModal: (modalId: string) => {
    set({ activeModal: modalId });
  },

  closeModal: () => {
    set({ activeModal: null });
  },

  addToast: (toast) => {
    const id = generateToastId();
    const duration = toast.duration ?? 5000;
    const newToast: Toast = { ...toast, id, duration };

    set((state) => ({ toasts: [...state.toasts, newToast] }));

    if (duration > 0) {
      const timeout = setTimeout(() => {
        get().removeToast(id);
        toastTimeouts.delete(id);
      }, duration);
      toastTimeouts.set(id, timeout);
    }

    const state = get();
    if (state.toasts.length > 10) {
      devWarn('High toast queue', { count: state.toasts.length });
    }
  },

  removeToast: (id: string) => {
    const timeout = toastTimeouts.get(id);
    if (timeout) {
      clearTimeout(timeout);
      toastTimeouts.delete(id);
    }
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },

  showSuccess: (title, message) => get().addToast({ type: 'success', title, message }),
  showError: (title, message) => get().addToast({ type: 'error', title, message }),
  showWarning: (title, message) => get().addToast({ type: 'warning', title, message }),
  showInfo: (title, message) => get().addToast({ type: 'info', title, message }),
}));
