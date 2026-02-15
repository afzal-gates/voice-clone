import { useState, useCallback } from 'react';
import type { ToastType } from '../components/ui/Toast';

export interface ToastConfig {
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
}

export interface ToastItem extends ToastConfig {
  id: string;
}

export const useToast = () => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((config: ToastConfig) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const toast: ToastItem = { ...config, id };

    setToasts((prev) => [...prev, toast]);

    return id;
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const success = useCallback(
    (message: string, title?: string, duration?: number) => {
      return showToast({ type: 'success', message, title, duration });
    },
    [showToast]
  );

  const error = useCallback(
    (message: string, title?: string, duration?: number) => {
      return showToast({ type: 'error', message, title, duration });
    },
    [showToast]
  );

  const warning = useCallback(
    (message: string, title?: string, duration?: number) => {
      return showToast({ type: 'warning', message, title, duration });
    },
    [showToast]
  );

  const info = useCallback(
    (message: string, title?: string, duration?: number) => {
      return showToast({ type: 'info', message, title, duration });
    },
    [showToast]
  );

  return {
    toasts,
    showToast,
    dismissToast,
    success,
    error,
    warning,
    info,
  };
};
