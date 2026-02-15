/**
 * Type definitions for audio mixer feature
 */

export interface MixParameters {
  tts_volume: number; // 0-100
  music_volume: number; // 0-100
  music_delay: number; // 0-5 seconds
  fade_in?: number; // Optional fade in duration (seconds)
  fade_out?: number; // Optional fade out duration (seconds)
}

export interface MixRequest {
  tts_job_id: string;
  music_job_id: string;
  parameters: MixParameters;
}

export interface MixResponse {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  output_file?: string;
  duration?: number;
  error?: string;
  progress?: number;
}

export interface MixJob {
  job_id: string;
  type: "tts" | "music";
  text?: string; // For TTS jobs
  prompt?: string; // For Music jobs
  duration?: number;
  created_at: string;
  status: string;
  output_file?: string;
}
