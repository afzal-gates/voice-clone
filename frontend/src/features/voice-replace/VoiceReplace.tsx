import React from 'react';
import { FileUploadCard } from './components/FileUploadCard';
import { ProcessingCard } from './components/ProcessingCard';
import { SpeakerList } from './components/SpeakerList';
import { ResultsCard } from './components/ResultsCard';
import { ErrorCard } from './components/ErrorCard';
import { useJobProcessing } from './hooks/useJobProcessing';
import { useVoiceAssignment } from './hooks/useVoiceAssignment';
import { useJobStore } from '@/store/jobStore';
import { JobStatus } from '@/types/job.types';
import './voice-replace.styles.css';

export const VoiceReplace: React.FC = () => {
  const { currentJobId, setCurrentJob } = useJobStore();

  const {
    job,
    loading,
    error: jobError,
    isProcessing,
    isAwaitingAssignment,
    retry,
    startPolling
  } = useJobProcessing({
    jobId: currentJobId,
    onComplete: (completedJob) => {
      console.log('Job completed:', completedJob);
    },
    onError: (error) => {
      console.error('Job error:', error);
    }
  });

  const {
    assignments,
    voices,
    loading: assignmentLoading,
    loadingVoices,
    error: assignmentError,
    assignVoice,
    submitAssignments,
    allAssigned
  } = useVoiceAssignment({
    jobId: currentJobId,
    speakers: job?.speakers || [],
    onSuccess: () => {
      startPolling();
    },
    onError: (error) => {
      console.error('Assignment error:', error);
    }
  });

  const handleUploadSuccess = (jobId: string) => {
    setCurrentJob(jobId);
  };

  const handleStartNew = () => {
    setCurrentJob(null);
  };

  const handleRetry = () => {
    if (currentJobId) {
      retry();
    }
  };

  const renderContent = () => {
    if (!currentJobId) {
      return <FileUploadCard onUploadSuccess={handleUploadSuccess} />;
    }

    if (loading && !job) {
      return (
        <div className="voice-replace__loading">
          <div className="voice-replace__spinner"></div>
          <p>Loading job details...</p>
        </div>
      );
    }

    if (!job) {
      return (
        <ErrorCard
          error="Failed to load job details"
          onRetry={handleRetry}
          onStartNew={handleStartNew}
        />
      );
    }

    if (job.status === JobStatus.FAILED) {
      return (
        <ErrorCard
          error={job.error || 'An unknown error occurred'}
          onStartNew={handleStartNew}
        />
      );
    }

    if (job.status === JobStatus.COMPLETED) {
      return <ResultsCard job={job} onStartNew={handleStartNew} />;
    }

    if (isAwaitingAssignment) {
      return (
        <SpeakerList
          speakers={job.speakers}
          voices={voices}
          loadingVoices={loadingVoices}
          assignments={assignments}
          onAssign={assignVoice}
          onSubmit={submitAssignments}
          submitting={assignmentLoading}
          allAssigned={allAssigned}
        />
      );
    }

    if (isProcessing) {
      return <ProcessingCard job={job} />;
    }

    return <ProcessingCard job={job} />;
  };

  return (
    <div className="voice-replace">
      <div className="voice-replace__container">
        <div className="voice-replace__header">
          <h1 className="voice-replace__title">Voice Replacement</h1>
          <p className="voice-replace__subtitle">
            Replace voices in your videos and audio files with AI-generated speech
          </p>
        </div>

        <div className="voice-replace__content">{renderContent()}</div>

        {(jobError || assignmentError) && (
          <div className="voice-replace__error-toast">
            <svg
              className="voice-replace__error-toast-icon"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                clipRule="evenodd"
              />
            </svg>
            <span>{jobError || assignmentError}</span>
          </div>
        )}
      </div>
    </div>
  );
};
