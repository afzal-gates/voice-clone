/**
 * API Configuration
 *
 * Centralized configuration for API base URLs and endpoints
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

/**
 * API Endpoints
 */
export const API_ENDPOINTS = {
  // Health & Settings
  health: '/api/health',
  settings: '/api/settings',
  ttsModels: '/api/tts-models',

  // Job Management
  uploadFile: '/api/upload',
  getJobs: '/api/jobs',
  getJob: (id: string) => `/api/jobs/${id}`,
  assignVoices: (id: string) => `/api/jobs/${id}/assign-voices`,
  downloadJob: (id: string) => `/api/jobs/${id}/download`,
  deleteJob: (id: string) => `/api/jobs/${id}`,
  addReferenceVoice: (id: string) => `/api/jobs/${id}/reference-voice`,

  // Voice Management
  getVoices: '/api/voices',
  getVoice: (id: string) => `/api/voices/${id}`,
  createVoice: '/api/voices',
  deleteVoice: (id: string) => `/api/voices/${id}`,
  getVoiceAudio: (id: string) => `/api/voices/${id}/audio`,
  createVoiceFromJob: (id: string) => `/api/voices/from-job/${id}`,

  // TTS
  generateTTS: '/api/tts',

  // Singing Synthesis
  generateSinging: '/api/singing',
  getSingingStatus: (id: string) => `/api/singing/${id}`,
  listSingingModels: '/api/singing/models',
  downloadSinging: (id: string) => `/api/singing/${id}/download`,
};

/**
 * WebSocket Endpoints
 */
export const WS_ENDPOINTS = {
  voiceChanger: '/ws/voice-changer',
  realtimeControl: '/ws/realtime-control',
};
