/**
 * Instrumental Music Generation Service
 *
 * API service for instrumental-only music generation operations
 */

import { apiGet, apiPost } from './api.service';
import type {
  InstrumentalRequest,
  InstrumentalResponse,
} from '@/types/instrumental.types';

/**
 * Generate instrumental music from lyrics (no vocals)
 */
export const generateInstrumental = async (
  request: InstrumentalRequest
): Promise<InstrumentalResponse> => {
  return apiPost<InstrumentalResponse>('/api/music/generate-instrumental', request);
};

/**
 * Get instrumental generation job status by job ID
 */
export const getInstrumentalStatus = async (
  jobId: string
): Promise<InstrumentalResponse> => {
  return apiGet<InstrumentalResponse>(`/api/music/generate-instrumental/${jobId}`);
};

/**
 * Get download URL for specific instrumental output
 */
export const downloadInstrumentalOutput = (
  jobId: string,
  outputType: string
): string => {
  return `/api/music/generate-instrumental/${jobId}/download/${outputType}`;
};

/**
 * Poll instrumental generation status until completion or failure
 */
export const pollInstrumentalStatus = async (
  jobId: string,
  onProgress?: (status: InstrumentalResponse) => void,
  pollInterval: number = 2000,
  maxAttempts: number = 600 // 20 minutes max
): Promise<InstrumentalResponse> => {
  let attempts = 0;

  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getInstrumentalStatus(jobId);

        if (onProgress) {
          onProgress(status);
        }

        if (status.status === 'completed') {
          resolve(status);
          return;
        }

        if (status.status === 'failed') {
          reject(new Error(status.error || 'Instrumental generation failed'));
          return;
        }

        attempts++;
        if (attempts >= maxAttempts) {
          reject(new Error('Instrumental generation timeout'));
          return;
        }

        setTimeout(poll, pollInterval);
      } catch (error) {
        reject(error);
      }
    };

    poll();
  });
};
