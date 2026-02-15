/**
 * Singing Synthesis Service
 *
 * API service for DiffSinger singing synthesis operations
 */

import { apiGet, apiPost } from './api.service';
import type { SingingRequest, SingingResponse, SingingVoiceModel } from '@/types/singing.types';

/**
 * Generate singing from lyrics and melody
 */
export const generateSinging = async (request: SingingRequest): Promise<SingingResponse> => {
  const formData = new FormData();

  formData.append('lyrics', request.lyrics);
  formData.append('voice_model', request.voice_model);
  formData.append('tempo', request.tempo.toString());
  formData.append('key_shift', request.key_shift.toString());

  if (request.melody) {
    formData.append('melody', request.melody);
  }

  if (request.melody_file) {
    formData.append('melody_file', request.melody_file);
  }

  return apiPost<SingingResponse>('/api/singing', formData);
};

/**
 * Get singing job status by job ID
 */
export const getSingingStatus = async (jobId: string): Promise<SingingResponse> => {
  return apiGet<SingingResponse>(`/api/singing/${jobId}`);
};

/**
 * Get list of available singing voice models
 */
export const listSingingModels = async (): Promise<SingingVoiceModel[]> => {
  const response = await apiGet<{ models: SingingVoiceModel[] }>('/api/singing-models');
  return response.models;
};

/**
 * Get download URL for singing output
 */
export const downloadSinging = (jobId: string, format: 'wav' | 'mp3' = 'wav'): string => {
  return `/api/singing/${jobId}/download?format=${format}`;
};

/**
 * Poll singing job status until completion or failure
 */
export const pollSingingStatus = async (
  jobId: string,
  onProgress?: (status: SingingResponse) => void,
  pollInterval: number = 1000,
  maxAttempts: number = 300
): Promise<SingingResponse> => {
  let attempts = 0;

  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getSingingStatus(jobId);

        if (onProgress) {
          onProgress(status);
        }

        if (status.status === 'completed') {
          resolve(status);
          return;
        }

        if (status.status === 'failed') {
          reject(new Error(status.error || 'Singing synthesis failed'));
          return;
        }

        attempts++;
        if (attempts >= maxAttempts) {
          reject(new Error('Singing synthesis timeout'));
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
