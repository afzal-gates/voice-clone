/**
 * Instrumental Music Generation Type Definitions
 *
 * Types for the "Only Music" feature that generates instrumental
 * music from lyrics without vocal synthesis.
 */

export type MusicGenre = 'pop' | 'rock' | 'edm' | 'classical' | 'cinematic' | 'hiphop' | 'jazz' | 'country' | 'folk' | 'ambient';
export type MusicMood = 'happy' | 'sad' | 'dark' | 'romantic' | 'epic' | 'calm' | 'energetic';

export interface InstrumentalRequest {
  lyrics: string;
  genre: MusicGenre;
  mood: MusicMood;
  bpm: number;
  instruments: string[] | null;
  title: string;
  duration: number;
}

export interface InstrumentalResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  outputs: {
    instrumental_wav?: string;
    instrumental_mp3?: string;
    midi?: string;
  } | null;
  progress: number;
  error: string | null;
}
