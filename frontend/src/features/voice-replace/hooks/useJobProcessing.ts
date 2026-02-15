import { useState, useEffect, useCallback, useRef } from 'react';
import { jobService } from '@/services/job.service';
import type { JobDetailResponse } from '@/types/job.types';
import { JobStatus } from '@/types/job.types';

interface UseJobProcessingOptions {
  jobId: string | null;
  pollingInterval?: number;
  onStatusChange?: (status: JobStatus) => void;
  onComplete?: (job: JobDetailResponse) => void;
  onError?: (error: string) => void;
}

export const useJobProcessing = (options: UseJobProcessingOptions) => {
  const {
    jobId,
    pollingInterval = 2000,
    onStatusChange,
    onComplete,
    onError
  } = options;

  const [job, setJob] = useState<JobDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const previousStatusRef = useRef<JobStatus | null>(null);
  const pollingTimeoutRef = useRef<number | null>(null);

  // Store callbacks in refs to avoid dependency issues
  const onStatusChangeRef = useRef(onStatusChange);
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  // Update refs when callbacks change
  useEffect(() => {
    onStatusChangeRef.current = onStatusChange;
    onCompleteRef.current = onComplete;
    onErrorRef.current = onError;
  }, [onStatusChange, onComplete, onError]);

  const fetchJob = useCallback(async () => {
    if (!jobId) return null;

    try {
      setLoading(true);
      const jobData = await jobService.getJob(jobId);
      setJob(jobData);
      setError(null);

      if (previousStatusRef.current !== jobData.status) {
        previousStatusRef.current = jobData.status;
        onStatusChangeRef.current?.(jobData.status);
      }

      if (jobData.status === JobStatus.COMPLETED) {
        onCompleteRef.current?.(jobData);
      }

      if (jobData.status === JobStatus.FAILED && jobData.error) {
        setError(jobData.error);
        onErrorRef.current?.(jobData.error);
      }

      return jobData;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch job';
      setError(errorMessage);
      onErrorRef.current?.(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  const startPolling = useCallback(() => {
    if (!jobId) return;

    // Clear any existing timeout
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }

    const poll = async () => {
      const currentJob = await fetchJob();

      if (currentJob && !isTerminalStatus(currentJob.status)) {
        pollingTimeoutRef.current = window.setTimeout(poll, pollingInterval);
      } else {
        // Job completed or failed, clear timeout
        pollingTimeoutRef.current = null;
      }
    };

    poll();
  }, [jobId, pollingInterval, fetchJob]);

  const stopPolling = useCallback(() => {
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!jobId) return;

    // Start initial fetch and polling
    const poll = async () => {
      const currentJob = await fetchJob();

      // Only continue polling if job is not in terminal state
      if (currentJob && !isTerminalStatus(currentJob.status)) {
        pollingTimeoutRef.current = window.setTimeout(poll, pollingInterval);
      }
    };

    poll();

    // Cleanup on unmount or jobId change
    return () => {
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, pollingInterval]);

  const isTerminalStatus = (status: JobStatus): boolean => {
    return status === JobStatus.COMPLETED || status === JobStatus.FAILED;
  };

  const isProcessing = job?.status
    ? !isTerminalStatus(job.status) && job.status !== JobStatus.AWAITING_VOICE_ASSIGNMENT
    : false;

  const isAwaitingAssignment = job?.status === JobStatus.AWAITING_VOICE_ASSIGNMENT;

  const retry = useCallback(() => {
    setError(null);
    fetchJob();
  }, [fetchJob]);

  return {
    job,
    loading,
    error,
    isProcessing,
    isAwaitingAssignment,
    retry,
    stopPolling,
    startPolling
  };
};
