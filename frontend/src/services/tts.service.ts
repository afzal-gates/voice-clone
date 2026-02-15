/**
 * TTS Service
 *
 * API service for Text-to-Speech operations
 */

import { apiGet, apiPost } from './api.service';
import type { TTSRequest, TTSResponse, TTSModel, VoiceProfile } from '@/types/tts.types';

/**
 * Generate speech from text
 */
export const generateSpeech = async (request: TTSRequest): Promise<TTSResponse> => {
  const formData = new FormData();

  formData.append('text', request.text);

  if (request.voice_id) {
    formData.append('voice_id', request.voice_id);
  }

  if (request.language) {
    formData.append('language', request.language);
  }

  if (request.tts_model) {
    formData.append('tts_model', request.tts_model);
  }

  if (request.speed !== undefined) {
    formData.append('speed', request.speed.toString());
  }

  if (request.pitch !== undefined) {
    formData.append('pitch', request.pitch.toString());
  }

  if (request.ref_text) {
    formData.append('ref_text', request.ref_text);
  }

  if (request.reference_audio) {
    formData.append('reference_audio', request.reference_audio);
  }

  return apiPost<TTSResponse>('/api/tts', formData);
};

/**
 * Get TTS status by job ID
 */
export const getTTSStatus = async (jobId: string): Promise<TTSResponse> => {
  return apiGet<TTSResponse>(`/api/tts/${jobId}`);
};

/**
 * Get available TTS models
 */
export const getModels = async (): Promise<TTSModel[]> => {
  return apiGet<TTSModel[]>('/api/tts-models');
};

/**
 * Get voice library
 */
export const getVoices = async (): Promise<VoiceProfile[]> => {
  const backendVoices = await apiGet<any[]>('/api/voices');

  // Transform backend response: voice_id → id, add category field
  return backendVoices.map((voice) => ({
    id: voice.voice_id,
    name: voice.name,
    duration: voice.duration,
    category: voice.category || 'custom',
    audioUrl: `/api/voices/${voice.voice_id}/audio`,
    createdAt: voice.created_at,
    metadata: {
      sample_rate: voice.sample_rate,
      description: voice.description,
    },
  }));
};

/**
 * Get voice preview audio URL
 */
export const getVoicePreviewUrl = (voiceId: string): string => {
  return `/api/voices/${voiceId}/audio`;
};

/**
 * Upload a new voice to library
 */
export const uploadVoice = async (
  audioFile: File,
  name: string,
  description?: string
): Promise<VoiceProfile> => {
  const formData = new FormData();
  formData.append('audio', audioFile);
  formData.append('name', name);
  if (description) {
    formData.append('description', description);
  }

  const response = await apiPost<any>('/api/voices', formData);

  // Transform response to match VoiceProfile interface
  return {
    id: response.voice_id,
    name: response.name,
    duration: response.duration,
    category: response.category || 'custom',
    audioUrl: `/api/voices/${response.voice_id}/audio`,
    createdAt: response.created_at,
    metadata: {
      sample_rate: response.sample_rate,
      description: response.description,
    },
  };
};

/**
 * Delete a voice from library
 */
export const deleteVoice = async (voiceId: string): Promise<void> => {
  return apiPost(`/api/voices/${voiceId}/delete`);
};

/**
 * Save generated audio as voice profile
 */
export const saveAsVoice = async (audioFile: string, name: string): Promise<VoiceProfile> => {
  return apiPost<VoiceProfile>('/api/voices/save', {
    audio_file: audioFile,
    name: name,
  });
};

/**
 * Poll TTS job status until completion or failure
 */
export const pollTTSStatus = async (
  jobId: string,
  onProgress?: (status: TTSResponse) => void,
  pollInterval: number = 1000,
  maxAttempts: number = 300
): Promise<TTSResponse> => {
  let attempts = 0;

  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getTTSStatus(jobId);

        if (onProgress) {
          onProgress(status);
        }

        if (status.status === 'completed') {
          resolve(status);
          return;
        }

        if (status.status === 'failed') {
          reject(new Error(status.error || 'TTS generation failed'));
          return;
        }

        attempts++;
        if (attempts >= maxAttempts) {
          reject(new Error('TTS generation timeout'));
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
