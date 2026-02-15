/**
 * Shared Component Types
 *
 * Common type definitions used across multiple components
 */

// Re-export component types for convenience
export type { ButtonProps } from './ui/Button';
export type { CardProps } from './ui/Card';
export type { InputProps } from './ui/Input';
export type { TextareaProps } from './ui/Textarea';
export type { SelectProps, SelectOption } from './ui/Select';
export type { ProgressBarProps } from './ui/ProgressBar';
export type { StatusBadgeProps, StatusType } from './ui/StatusBadge';
export type { ModalProps } from './ui/Modal';
export type { TabsProps, Tab } from './ui/Tabs';
export type { ToastProps, ToastType } from './ui/Toast';
export type { ToastContainerProps } from './ui/ToastContainer';
export type { AudioPlayerProps } from './audio/AudioPlayer';
export type { HeaderProps } from './layout/Header';
export type { MainLayoutProps } from './layout/MainLayout';
export type { TabContainerProps } from './layout/TabContainer';

// Common component props patterns
export interface BaseComponentProps {
  className?: string;
}

export interface WithChildren {
  children: React.ReactNode;
}

export interface WithLabel {
  label?: string;
}

export interface WithError {
  error?: string;
}

export interface FormFieldProps extends WithLabel, WithError, BaseComponentProps {}
