/**
 * useTTSGeneration Hook
 *
 * Custom hook for TTS generation with polling
 */

import { useState, useCallback } from 'react';
import { generateSpeech, pollTTSStatus } from '@/services/tts.service';
import type { TTSRequest, TTSResponse } from '@/types/tts.types';

interface UseTTSGenerationReturn {
  isGenerating: boolean;
  progress: number;
  error: string | null;
  result: TTSResponse | null;
  generate: (request: TTSRequest) => Promise<void>;
  reset: () => void;
}

export const useTTSGeneration = (): UseTTSGenerationReturn => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TTSResponse | null>(null);

  const generate = useCallback(async (request: TTSRequest) => {
    setIsGenerating(true);
    setProgress(0);
    setError(null);
    setResult(null);

    try {
      // Start TTS job
      const response = await generateSpeech(request);

      // Poll for completion
      const finalResult = await pollTTSStatus(
        response.job_id,
        (status) => {
          // Update progress based on status
          if (status.status === 'processing') {
            setProgress(50);
          }
        }
      );

      setProgress(100);
      setResult(finalResult);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'TTS generation failed';
      setError(errorMessage);
    } finally {
      setIsGenerating(false);
    }
  }, []);

  const reset = useCallback(() => {
    setIsGenerating(false);
    setProgress(0);
    setError(null);
    setResult(null);
  }, []);

  return {
    isGenerating,
    progress,
    error,
    result,
    generate,
    reset,
  };
};
