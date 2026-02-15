/**
 * Type definitions for music generation feature
 */

export type MusicStyle =
  | "pop"
  | "rock"
  | "electronic"
  | "classical"
  | "jazz"
  | "ambient"
  | "hip-hop"
  | "country"
  | "folk"
  | "cinematic";

export interface MusicRequest {
  prompt: string;
  duration: number;
  style?: MusicStyle;
  reference_audio?: File;
}

export interface MusicResponse {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  output_file?: string;
  duration?: number;
  error?: string;
}

export interface MusicParameters {
  duration: number;
  style?: MusicStyle;
  referenceAudio?: File;
}

export const MUSIC_STYLES: { value: MusicStyle; label: string; description: string }[] = [
  { value: "pop", label: "Pop", description: "Catchy melodies with upbeat rhythm" },
  { value: "rock", label: "Rock", description: "Energetic guitar-driven sound" },
  { value: "electronic", label: "Electronic", description: "Synthesizers and electronic beats" },
  { value: "classical", label: "Classical", description: "Orchestral arrangements" },
  { value: "jazz", label: "Jazz", description: "Smooth improvisational style" },
  { value: "ambient", label: "Ambient", description: "Atmospheric soundscapes" },
  { value: "hip-hop", label: "Hip-Hop", description: "Rhythmic beats and bass" },
  { value: "country", label: "Country", description: "Acoustic guitar and storytelling" },
  { value: "folk", label: "Folk", description: "Traditional acoustic instruments" },
  { value: "cinematic", label: "Cinematic", description: "Epic orchestral soundtrack" },
];
