/**
 * UI Store
 *
 * Manages UI state (tabs, modals, toasts)
 */

import { create } from 'zustand';

interface Toast {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  message: string;
}

interface UIStore {
  // State
  activeTab: number;
  isSettingsOpen: boolean;
  toasts: Toast[];

  // Actions
  setActiveTab: (tab: number) => void;
  openSettings: () => void;
  closeSettings: () => void;
  showToast: (toast: Omit<Toast, 'id'>) => void;
  dismissToast: (id: string) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  // Initial state
  activeTab: 0,
  isSettingsOpen: false,
  toasts: [],

  // Actions
  setActiveTab: (tab) => {
    set({ activeTab: tab });
  },

  openSettings: () => {
    set({ isSettingsOpen: true });
  },

  closeSettings: () => {
    set({ isSettingsOpen: false });
  },

  showToast: (toast) => {
    const id = `toast-${Date.now()}`;
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }],
    }));

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }));
    }, 5000);
  },

  dismissToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    }));
  },
}));
