import React from 'react';
import './ProgressBar.css';

export interface ProgressBarProps {
  progress: number; // 0-100
  indeterminate?: boolean;
  className?: string;
  label?: string;
  showPercentage?: boolean;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  progress,
  indeterminate = false,
  className,
  label,
  showPercentage = false,
}) => {
  const clampedProgress = Math.min(Math.max(progress, 0), 100);

  return (
    <div className={`progress-wrapper ${className || ''}`}>
      {(label || showPercentage) && (
        <div className="progress-header">
          {label && <span className="progress-label">{label}</span>}
          {showPercentage && !indeterminate && (
            <span className="progress-percentage">{Math.round(clampedProgress)}%</span>
          )}
        </div>
      )}
      <div
        className="progress-bar"
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : clampedProgress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label || 'Progress'}
      >
        <div
          className={`progress-fill ${indeterminate ? 'progress-indeterminate' : ''}`}
          style={indeterminate ? undefined : { width: `${clampedProgress}%` }}
        />
      </div>
    </div>
  );
};
