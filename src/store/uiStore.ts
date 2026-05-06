import { create } from 'zustand';
import {
  applyThemePreset,
  enableHighContrast,
  getCurrentThemePreset,
  getHighContrastPreference,
} from '../theme/theme';
import { devWarn, devError } from '../utils/dev-log';

interface UIState {
  // Theme state
  highContrast: boolean;
  currentTheme: 'default' | 'nocturne' | 'ember';

  // UI state
  sidebarOpen: boolean;
  chatSidebarOpen: boolean;
  activeModal: string | null;
  notifications: NotificationItem[];

  // Actions
  setHighContrast: (enabled: boolean) => void;
  setTheme: (theme: 'default' | 'nocturne' | 'ember') => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleChatSidebar: () => void;
  setChatSidebarOpen: (open: boolean) => void;
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
// Counter for generating unique notification IDs (prevents collisions)
let notificationIdCounter = 0;
const generateNotificationId = (): string => {
  notificationIdCounter += 1;
  return `notification-${notificationIdCounter}-${Date.now()}`;
};

// Track active notification timeouts so we can clear them if needed
const notificationTimeouts = new Map<string, NodeJS.Timeout>();

// Track notification metrics for debugging
const notificationMetrics = {
  totalCreated: 0,
  totalRemoved: 0,
  activeCount: 0,
};

// Helper to load persisted theme preference
const _getPersistedTheme = (): 'default' | 'nocturne' | 'ember' => {
  const persisted = getCurrentThemePreset();
  return persisted === 'nocturne' ||
    persisted === 'ember' ||
    persisted === 'default'
    ? persisted
    : 'default';
};

export const useUIStore = create<UIState>((set, get) => ({
  // Initial state
  highContrast: getHighContrastPreference(),
  currentTheme: _getPersistedTheme(),
  sidebarOpen: true,
  chatSidebarOpen: false,
  activeModal: null,
  notifications: [],

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
    root.classList.remove(
      'theme-default',
      'theme-nocturne',
      'theme-ember',
    );
    root.classList.add(`theme-${theme}`);
  },

  // Sidebar actions
  toggleSidebar: () => {
    set((state) => ({ sidebarOpen: !state.sidebarOpen }));
  },

  setSidebarOpen: (open: boolean) => {
    set({ sidebarOpen: open });
  },

  toggleChatSidebar: () => {
    set((state) => ({
      chatSidebarOpen: !state.chatSidebarOpen,
    }));
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

  // Notification actions
  addNotification: (notification) => {
    const id = generateNotificationId();
    const newNotification: NotificationItem = {
      id,
      duration: 5000, // Default 5 seconds
      ...notification,
    };

    notificationMetrics.totalCreated++;
    notificationMetrics.activeCount++;

    set((state) => ({
      notifications: [...state.notifications, newNotification],
    }));

    // Log long-running notifications
    if (newNotification.type === 'error') {
      devError(
        'Error notification added',
        {
          id,
          title: newNotification.title,
          message: newNotification.message,
          duration: newNotification.duration,
        },
      );
    }

    // Auto-remove after duration
    if (
      newNotification.duration &&
      newNotification.duration > 0
    ) {
      const timeout = setTimeout(() => {
        get().removeNotification(id);
        notificationTimeouts.delete(id);
      }, newNotification.duration);

      notificationTimeouts.set(id, timeout);
    }
  },

  removeNotification: (id: string) => {
    // Cancel any pending timeout for this notification
    const timeout = notificationTimeouts.get(id);
    if (timeout) {
      clearTimeout(timeout);
      notificationTimeouts.delete(id);
    }

    notificationMetrics.totalRemoved++;
    notificationMetrics.activeCount = Math.max(
      0,
      notificationMetrics.activeCount - 1,
    );

    set((state) => ({
      notifications: state.notifications.filter(
        (n) => n.id !== id,
      ),
    }));

    // Warn if too many notifications are queued
    const state = get();
    if (state.notifications.length > 10) {
      devWarn(
        'High notification queue',
        {
          count: state.notifications.length,
          metrics: notificationMetrics,
        },
      );
    }
  },
}));
