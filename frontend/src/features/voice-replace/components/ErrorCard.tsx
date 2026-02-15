import React from 'react';
import { Card } from '@/components';
import { Button } from '@/components';
import { StatusBadge } from '@/components';

interface ErrorCardProps {
  error: string;
  onRetry?: () => void;
  onStartNew: () => void;
}

export const ErrorCard: React.FC<ErrorCardProps> = ({ error, onRetry, onStartNew }) => {
  return (
    <Card>
      <div className="error-card">
        <div className="error-card__header">
          <StatusBadge status="error">Failed</StatusBadge>
          <h2 className="error-card__title">Processing Failed</h2>
        </div>

        <div className="error-card__content">
          <div className="error-card__icon">
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
          </div>

          <div className="error-card__message">
            <h3 className="error-card__message-title">Error Details</h3>
            <p className="error-card__message-text">{error}</p>
          </div>

          <div className="error-card__suggestions">
            <h4 className="error-card__suggestions-title">What you can try:</h4>
            <ul className="error-card__suggestions-list">
              <li>Check if your file is in a supported format (MP4, AVI, MKV, MP3, WAV)</li>
              <li>Ensure the file is not corrupted</li>
              <li>Try a smaller file if the issue persists</li>
              <li>Contact support if the problem continues</li>
            </ul>
          </div>
        </div>

        <div className="error-card__actions">
          {onRetry && (
            <Button variant="primary" onClick={onRetry} fullWidth>
              Retry Processing
            </Button>
          )}
          <Button variant="outline" onClick={onStartNew} fullWidth>
            Upload New File
          </Button>
        </div>
      </div>
    </Card>
  );
};
