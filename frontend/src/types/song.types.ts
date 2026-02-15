/**
 * Type definitions for Complete Song Generation feature
 */

export type MusicGenre = 'pop' | 'rock' | 'edm' | 'classical' | 'cinematic' | 'hiphop' | 'jazz' | 'country' | 'folk' | 'ambient';

export type MusicMood = 'happy' | 'sad' | 'dark' | 'romantic' | 'epic' | 'calm' | 'energetic';

export type VocalType = 'male' | 'female' | 'choir' | 'ai';

export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface CompleteSongRequest {
  lyrics: string;
  genre: MusicGenre;
  mood: MusicMood;
  bpm: number;
  instruments?: string[];
  vocal_type: VocalType;
  language: string;
  song_title: string;
  artist_name: string;
  generate_video: boolean;
  duration: number;
}

export interface CompleteSongResponse {
  job_id: string;
  status: JobStatus;
  outputs?: SongOutputs;
  progress: number;
  error?: string;
}

export interface SongOutputs {
  mixed_song_wav?: string;
  mixed_song_mp3?: string;
  instrumental_wav?: string;
  instrumental_mp3?: string;
  vocals_wav?: string;
  vocals_mp3?: string;
  midi?: string;
  video?: string;
}

export interface SongGeneratorState {
  // Form state
  lyrics: string;
  genre: MusicGenre;
  mood: MusicMood;
  bpm: number;
  instruments: string[];
  vocalType: VocalType;
  language: string;
  songTitle: string;
  artistName: string;
  generateVideo: boolean;
  duration: number;

  // Job state
  jobId: string | null;
  status: JobStatus | null;
  outputs: SongOutputs | null;
  progress: number;
  error: string | null;

  // UI state
  isGenerating: boolean;
  showAdvanced: boolean;
}
