/**
 * Type definitions for singing synthesis feature
 */

export type MelodyMode = 'auto' | 'notation' | 'midi';

export interface SingingRequest {
  lyrics: string;
  melody?: string; // ABC notation or "auto"
  melody_file?: File; // MIDI file
  voice_model: string;
  tempo: number; // 60-200 BPM
  key_shift: number; // -12 to +12 semitones
}

export interface SingingResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  output_file?: string;
  duration?: number;
  error?: string;
}

export interface SingingVoiceModel {
  model_id: string;
  name: string;
  language: string;
  description: string;
}

export interface SingingParameters {
  tempo: number;
  keyShift: number;
}

export interface SingingGenerationState {
  isGenerating: boolean;
  jobId: string | null;
  progress: number;
  error: string | null;
  result: SingingResponse | null;
}

// Example lyrics templates
export const EXAMPLE_LYRICS = {
  'Five Little Ducks': `Five little ducks went out one day
Over the hills and far away
Mother duck said "Quack, quack, quack, quack"
But only four little ducks came back`,

  'Twinkle Star': `Twinkle, twinkle, little star
How I wonder what you are
Up above the world so high
Like a diamond in the sky
Twinkle, twinkle, little star
How I wonder what you are`,

  'Happy Birthday': `Happy birthday to you
Happy birthday to you
Happy birthday dear friend
Happy birthday to you`,

  'Row Your Boat': `Row, row, row your boat
Gently down the stream
Merrily, merrily, merrily, merrily
Life is but a dream`,
};

// Example melody notations (note:duration format)
export const EXAMPLE_NOTATION = {
  'Simple Scale': 'C4:0.5 D4:0.5 E4:0.5 F4:0.5 G4:0.5 A4:0.5 B4:0.5 C5:1.0',
  'Twinkle Pattern': 'C4:1.0 C4:1.0 G4:1.0 G4:1.0 A4:1.0 A4:1.0 G4:2.0',
  'Happy Birthday': 'C4:0.75 C4:0.25 D4:1.0 C4:1.0 F4:1.0 E4:2.0',
  'Descending': 'C5:0.5 B4:0.5 A4:0.5 G4:0.5 F4:0.5 E4:0.5 D4:0.5 C4:1.0',
};

export const SINGING_HELP_TEXT = {
  lyrics: 'Enter the lyrics you want to synthesize. Each line will be matched with the melody.',
  melodyAuto: 'Automatically generate a natural melody based on the lyrics prosody and rhythm.',
  melodyNotation: 'Provide melody in notation format: Note:Duration (e.g., C4:1.0 D4:0.5 E4:0.5)',
  melodyMidi: 'Upload a MIDI file containing the melody. The lyrics will be aligned to the notes.',
  tempo: 'Control the speed of the singing. 120 BPM is typical for pop songs.',
  keyShift: 'Transpose the melody up or down by semitones. +2 raises by a whole step.',
  voice: 'Select the singing voice model. Different models have different vocal characteristics.',
};
