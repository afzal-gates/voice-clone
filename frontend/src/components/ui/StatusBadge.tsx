import React from 'react';
import './StatusBadge.css';

export type StatusType = 'success' | 'error' | 'warning' | 'info' | 'pending';

export interface StatusBadgeProps {
  status: StatusType;
  children: React.ReactNode;
  className?: string;
  withDot?: boolean;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  children,
  className,
  withDot = true,
}) => {
  return (
    <span className={`status-badge status-badge-${status} ${className || ''}`} role="status">
      {withDot && <span className="status-dot" aria-hidden="true" />}
      {children}
    </span>
  );
};
