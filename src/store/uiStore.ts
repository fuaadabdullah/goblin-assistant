import { create } from 'zustand';
import { enableHighContrast, getHighContrastPreference } from '../theme/theme';

interface UIState {
  // Theme state
  highContrast: boolean;
  currentTheme: 'default' | 'nocturne' | 'ember';

  // UI state
  sidebarOpen: boolean;
  activeModal: string | null;
  notifications: NotificationItem[];

  // Actions
  setHighContrast: (enabled: boolean) => void;
  setTheme: (theme: 'default' | 'nocturne' | 'ember') => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  openModal: (modalId: string) => void;
  closeModal: () => void;
  addNotification: (notification: Omit<NotificationItem, 'id'>) => void;
  removeNotification: (id: string) => void;
}

interface NotificationItem {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
}

/**
 * Zustand store for UI state management
 * Handles theme preferences, modals, notifications, and other UI concerns
 */
// Helper to load persisted theme preference
const _getPersistedTheme = (): 'default' | 'nocturne' | 'ember' => {
  if (typeof window === 'undefined') return 'default';
  try {
    const persisted = localStorage.getItem('goblin-theme');
    if (
      persisted === 'nocturne' ||
      persisted === 'ember' ||
      persisted === 'default'
    ) {
      return persisted;
    }
  } catch (e) {
    // localStorage may not be available
  }
  return 'default';
};

export const useUIStore = create<UIState>((set, get) => ({
  // Initial state
  highContrast: getHighContrastPreference(),
  currentTheme: _getPersistedTheme(),
  sidebarOpen: true,
  activeModal: null,
  notifications: [],

  // Theme actions
  setHighContrast: (enabled: boolean) => {
    enableHighContrast(enabled);
    set({ highContrast: enabled });
  },

  setTheme: (theme: 'default' | 'nocturne' | 'ember') => {
    set({ currentTheme: theme });
    // Apply theme to document root
    const root = document.documentElement;
    root.setAttribute('data-theme', theme);
    // Also update via CSS class for broader compatibility
    root.classList.remove('theme-default', 'theme-nocturne', 'theme-ember');
    root.classList.add(`theme-${theme}`);
    // Persist theme preference
    try {
      localStorage.setItem('goblin-theme', theme);
    } catch (e) {
      console.warn('Failed to persist theme preference:', e);
    }
  },

  // Sidebar actions
  toggleSidebar: () => {
    set((state) => ({ sidebarOpen: !state.sidebarOpen }));
  },

  setSidebarOpen: (open: boolean) => {
    set({ sidebarOpen: open });
  },

  // Modal actions
  openModal: (modalId: string) => {
    set({ activeModal: modalId });
  },

  closeModal: () => {
    set({ activeModal: null });
  },

  // Notification actions
  addNotification: (notification) => {
    const id = Date.now().toString();
    const newNotification: NotificationItem = {
      id,
      duration: 5000, // Default 5 seconds
      ...notification,
    };

    set((state) => ({
      notifications: [...state.notifications, newNotification],
    }));

    // Auto-remove after duration
    if (newNotification.duration && newNotification.duration > 0) {
      setTimeout(() => {
        get().removeNotification(id);
      }, newNotification.duration);
    }
  },

  removeNotification: (id: string) => {
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    }));
  },
}));
