import React from 'react';
import { JobStatus, JobStatusLabels } from '@/types/job.types';

interface PipelineStepperProps {
  currentStatus: JobStatus;
}

interface Step {
  status: JobStatus;
  label: string;
}

const PIPELINE_STEPS: Step[] = [
  { status: JobStatus.PENDING, label: 'Queued' },
  { status: JobStatus.EXTRACTING_AUDIO, label: 'Extract Audio' },
  { status: JobStatus.SEPARATING, label: 'Separate' },
  { status: JobStatus.DIARIZING, label: 'Identify Speakers' },
  { status: JobStatus.TRANSCRIBING, label: 'Transcribe' },
  { status: JobStatus.AWAITING_VOICE_ASSIGNMENT, label: 'Assign Voices' },
  { status: JobStatus.GENERATING_SPEECH, label: 'Generate Speech' },
  { status: JobStatus.ALIGNING, label: 'Align' },
  { status: JobStatus.MERGING, label: 'Merge' },
  { status: JobStatus.COMPLETED, label: 'Complete' }
];

export const PipelineStepper: React.FC<PipelineStepperProps> = ({ currentStatus }) => {
  const currentIndex = PIPELINE_STEPS.findIndex((step) => step.status === currentStatus);
  const isFailed = currentStatus === JobStatus.FAILED;

  const getStepStatus = (index: number): 'completed' | 'active' | 'pending' | 'failed' => {
    if (isFailed && index === currentIndex) return 'failed';
    if (index < currentIndex) return 'completed';
    if (index === currentIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="pipeline-stepper">
      <div className="pipeline-stepper__steps">
        {PIPELINE_STEPS.map((step, index) => {
          const stepStatus = getStepStatus(index);
          const isLast = index === PIPELINE_STEPS.length - 1;

          return (
            <div key={step.status} className="pipeline-stepper__step-wrapper">
              <div
                className={`pipeline-stepper__step pipeline-stepper__step--${stepStatus}`}
              >
                <div className="pipeline-stepper__step-indicator">
                  {stepStatus === 'completed' && (
                    <svg
                      className="pipeline-stepper__step-icon"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  {stepStatus === 'active' && (
                    <div className="pipeline-stepper__step-spinner">
                      <div className="pipeline-stepper__spinner"></div>
                    </div>
                  )}
                  {stepStatus === 'failed' && (
                    <svg
                      className="pipeline-stepper__step-icon"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                  )}
                  {stepStatus === 'pending' && (
                    <div className="pipeline-stepper__step-number">{index + 1}</div>
                  )}
                </div>
                <div className="pipeline-stepper__step-label">{step.label}</div>
              </div>
              {!isLast && (
                <div
                  className={`pipeline-stepper__connector pipeline-stepper__connector--${
                    index < currentIndex ? 'completed' : 'pending'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      <div className="pipeline-stepper__current-status">
        <strong>Status:</strong> {JobStatusLabels[currentStatus]}
      </div>
    </div>
  );
};
