/**
 * TTS (Text-to-Speech) Types
 *
 * Type definitions for TTS feature
 */

export interface TTSRequest {
  text: string;
  reference_audio?: File;
  voice_id?: string;
  language?: string;
  tts_model?: string;
  speed?: number; // 0.5-2.0
  pitch?: number; // 0.5-2.0
  ref_text?: string; // For IndicF5
}

export interface TTSResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  output_file?: string;
  error?: string;
}

export interface TTSModel {
  id: string;
  name: string;
  languages: string[];
  description?: string;
  requiresReferenceText?: boolean;
}

export interface VoiceProfile {
  id: string;
  name: string;
  duration?: number;
  category: 'realistic' | 'character' | 'custom';
  audioUrl?: string;
  createdAt?: string;
  metadata?: Record<string, any>;
}

export interface TTSGenerationState {
  isGenerating: boolean;
  jobId: string | null;
  progress: number;
  error: string | null;
  result: TTSResponse | null;
}

export interface TTSParameters {
  speed: number;
  pitch: number;
  refText?: string;
  referenceAudio?: File;
}

export type VoiceCategory = 'all' | 'realistic' | 'character' | 'custom';
