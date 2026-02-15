import { useState, useCallback } from 'react';
import { jobService } from '@/services/job.service';
import type { UploadProgress } from '@/types/job.types';
import { InputType } from '@/types/job.types';

interface UseFileUploadOptions {
  onSuccess?: (jobId: string) => void;
  onError?: (error: Error) => void;
  maxSizeMB?: number;
  acceptedTypes?: string[];
}

export const useFileUpload = (options: UseFileUploadOptions = {}) => {
  const {
    onSuccess,
    onError,
    maxSizeMB = 500,
    acceptedTypes = ['video/mp4', 'video/avi', 'video/mkv', 'audio/mpeg', 'audio/wav', 'audio/mp3']
  } = options;

  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<UploadProgress | null>(null);
  const [error, setError] = useState<string | null>(null);

  const validateFile = useCallback(
    (file: File): string | null => {
      if (!acceptedTypes.includes(file.type)) {
        return `File type not supported. Accepted types: ${acceptedTypes.join(', ')}`;
      }

      const maxSizeBytes = maxSizeMB * 1024 * 1024;
      if (file.size > maxSizeBytes) {
        return `File size exceeds ${maxSizeMB}MB limit`;
      }

      return null;
    },
    [acceptedTypes, maxSizeMB]
  );

  const detectInputType = (file: File): InputType => {
    if (file.type.startsWith('video/')) {
      return InputType.VIDEO;
    }
    return InputType.AUDIO;
  };

  const uploadFile = useCallback(
    async (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        onError?.(new Error(validationError));
        return;
      }

      setUploading(true);
      setError(null);
      setProgress({ loaded: 0, total: file.size, percentage: 0 });

      try {
        const inputType = detectInputType(file);
        const response = await jobService.uploadFile(file, inputType, (prog) => {
          setProgress(prog);
        });

        setUploading(false);
        setProgress(null);
        onSuccess?.(response.job_id);
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Upload failed');
        setError(error.message);
        setUploading(false);
        setProgress(null);
        onError?.(error);
      }
    },
    [validateFile, onSuccess, onError]
  );

  const resetUpload = useCallback(() => {
    setUploading(false);
    setProgress(null);
    setError(null);
  }, []);

  return {
    uploading,
    progress,
    error,
    uploadFile,
    validateFile,
    resetUpload
  };
};
