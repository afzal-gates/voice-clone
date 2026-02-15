/**
 * Status Indicator Component
 *
 * Shows connection and processing status
 */

import React from 'react';
import { StatusBadge } from '@/components/ui/StatusBadge';

interface StatusIndicatorProps {
  connected: boolean;
  connecting: boolean;
  processing: boolean;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  connected,
  connecting,
  processing,
}) => {
  const getConnectionStatus = () => {
    if (connecting) return { status: 'warning' as const, text: 'Connecting...' };
    if (connected) return { status: 'success' as const, text: 'Connected' };
    return { status: 'error' as const, text: 'Disconnected' };
  };

  const getProcessingStatus = () => {
    if (!connected) return { status: 'pending' as const, text: 'Not Ready' };
    if (processing) return { status: 'info' as const, text: 'Processing' };
    return { status: 'pending' as const, text: 'Ready' };
  };

  const connectionStatus = getConnectionStatus();
  const processingStatus = getProcessingStatus();

  return (
    <div className="status-indicator">
      <div className="status-indicator__item">
        <span className="status-indicator__label">Connection:</span>
        <StatusBadge status={connectionStatus.status}>
          {connectionStatus.text}
        </StatusBadge>
      </div>
      <div className="status-indicator__item">
        <span className="status-indicator__label">Status:</span>
        <StatusBadge status={processingStatus.status}>
          {processingStatus.text}
        </StatusBadge>
      </div>
    </div>
  );
};
