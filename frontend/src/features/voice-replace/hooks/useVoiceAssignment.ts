import { useState, useCallback, useEffect } from 'react';
import { jobService } from '@/services/job.service';
import type { VoiceAssignment, Speaker, Voice } from '@/types/job.types';

interface UseVoiceAssignmentOptions {
  jobId: string | null;
  speakers: Speaker[];
  onSuccess?: () => void;
  onError?: (error: Error) => void;
}

export const useVoiceAssignment = (options: UseVoiceAssignmentOptions) => {
  const { jobId, speakers, onSuccess, onError } = options;

  const [assignments, setAssignments] = useState<Map<string, string>>(new Map());
  const [voices, setVoices] = useState<Voice[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingVoices, setLoadingVoices] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchVoices = async () => {
      try {
        setLoadingVoices(true);
        const voiceList = await jobService.getVoices();
        setVoices(voiceList);
      } catch (err) {
        console.error('Failed to fetch voices:', err);
      } finally {
        setLoadingVoices(false);
      }
    };

    fetchVoices();
  }, []);

  const assignVoice = useCallback((speakerId: string, voiceRef: string) => {
    setAssignments((prev) => {
      const updated = new Map(prev);
      updated.set(speakerId, voiceRef);
      return updated;
    });
  }, []);

  const removeAssignment = useCallback((speakerId: string) => {
    setAssignments((prev) => {
      const updated = new Map(prev);
      updated.delete(speakerId);
      return updated;
    });
  }, []);

  const clearAssignments = useCallback(() => {
    setAssignments(new Map());
  }, []);

  const isComplete = useCallback(() => {
    return speakers.length > 0 && speakers.every((speaker) => assignments.has(speaker.speaker_id));
  }, [speakers, assignments]);

  const submitAssignments = useCallback(async () => {
    if (!jobId || !isComplete()) {
      setError('Please assign voices to all speakers');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const assignmentArray: VoiceAssignment[] = Array.from(assignments.entries()).map(
        ([speaker_id, voice_ref]) => ({
          speaker_id,
          voice_ref
        })
      );

      await jobService.assignVoices(jobId, assignmentArray);
      onSuccess?.();
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to assign voices');
      setError(error.message);
      onError?.(error);
    } finally {
      setLoading(false);
    }
  }, [jobId, assignments, isComplete, onSuccess, onError]);

  const getAssignment = useCallback(
    (speakerId: string): string | undefined => {
      return assignments.get(speakerId);
    },
    [assignments]
  );

  const assignmentCount = assignments.size;
  const totalSpeakers = speakers.length;
  const allAssigned = isComplete();

  return {
    assignments,
    voices,
    loading,
    loadingVoices,
    error,
    assignVoice,
    removeAssignment,
    clearAssignments,
    submitAssignments,
    getAssignment,
    assignmentCount,
    totalSpeakers,
    allAssigned
  };
};
