/**
 * Song Generation Service
 *
 * API service for complete AI song generation operations
 */

import { apiGet, apiPost } from './api.service';
import type {
  CompleteSongRequest,
  CompleteSongResponse,
} from '@/types/song.types';

/**
 * Generate complete AI song with instrumentals, vocals, and mixing
 */
export const generateCompleteSong = async (
  request: CompleteSongRequest
): Promise<CompleteSongResponse> => {
  return apiPost<CompleteSongResponse>('/api/music/generate-song', request);
};

/**
 * Get song generation job status by job ID
 */
export const getSongStatus = async (
  jobId: string
): Promise<CompleteSongResponse> => {
  return apiGet<CompleteSongResponse>(`/api/music/generate-song/${jobId}`);
};

/**
 * Get download URL for specific song output
 */
export const downloadSongOutput = (
  jobId: string,
  outputType: string
): string => {
  return `/api/music/generate-song/${jobId}/download/${outputType}`;
};

/**
 * Poll song generation status until completion or failure
 */
export const pollSongStatus = async (
  jobId: string,
  onProgress?: (status: CompleteSongResponse) => void,
  pollInterval: number = 2000,
  maxAttempts: number = 600 // 20 minutes max
): Promise<CompleteSongResponse> => {
  let attempts = 0;

  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getSongStatus(jobId);

        if (onProgress) {
          onProgress(status);
        }

        if (status.status === 'completed') {
          resolve(status);
          return;
        }

        if (status.status === 'failed') {
          reject(new Error(status.error || 'Song generation failed'));
          return;
        }

        attempts++;
        if (attempts >= maxAttempts) {
          reject(new Error('Song generation timeout'));
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
