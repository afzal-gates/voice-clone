import React from 'react';
import { Card } from '@/components';
import { ProgressBar } from '@/components';
import { PipelineStepper } from './PipelineStepper';
import type { JobDetailResponse } from '@/types/job.types';

interface ProcessingCardProps {
  job: JobDetailResponse;
}

export const ProcessingCard: React.FC<ProcessingCardProps> = ({ job }) => {
  const progressPercentage = Math.round(job.progress * 100);

  return (
    <Card>
      <div className="processing-card">
        <h2 className="processing-card__title">Processing Your File</h2>
        <p className="processing-card__filename">{job.input_filename}</p>

        <div className="processing-card__stepper">
          <PipelineStepper currentStatus={job.status} />
        </div>

        <div className="processing-card__progress">
          <div className="processing-card__progress-header">
            <span className="processing-card__progress-label">Overall Progress</span>
            <span className="processing-card__progress-value">{progressPercentage}%</span>
          </div>
          <ProgressBar progress={progressPercentage} />
        </div>

        <div className="processing-card__info">
          <div className="processing-card__info-item">
            <svg
              className="processing-card__info-icon"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="processing-card__info-text">
              Please wait while we process your file. This may take several minutes depending on
              the file size.
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
};
