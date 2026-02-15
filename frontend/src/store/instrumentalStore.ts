/**
 * Instrumental Music Generation Store
 *
 * Zustand store for managing instrumental generation state
 */

import { create } from 'zustand';
import type {
  InstrumentalRequest,
  InstrumentalResponse,
  MusicGenre,
  MusicMood,
} from '@/types/instrumental.types';
import {
  generateInstrumental,
  pollInstrumentalStatus,
} from '@/services/instrumental.service';

interface InstrumentalStore {
  // Form state
  lyrics: string;
  genre: MusicGenre;
  mood: MusicMood;
  bpm: number;
  instruments: string[];
  title: string;
  duration: number;

  // Generation state
  isGenerating: boolean;
  jobId: string | null;
  progress: number;
  status: 'idle' | 'pending' | 'processing' | 'completed' | 'failed';
  error: string | null;
  outputs: InstrumentalResponse['outputs'] | null;

  // Actions
  setLyrics: (lyrics: string) => void;
  setGenre: (genre: MusicGenre) => void;
  setMood: (mood: MusicMood) => void;
  setBpm: (bpm: number) => void;
  setInstruments: (instruments: string[]) => void;
  setTitle: (title: string) => void;
  setDuration: (duration: number) => void;

  generateMusic: () => Promise<void>;
  reset: () => void;
}

const initialState = {
  // Form state
  lyrics: '',
  genre: 'pop' as MusicGenre,
  mood: 'happy' as MusicMood,
  bpm: 120,
  instruments: [],
  title: 'Untitled Instrumental',
  duration: 30,

  // Generation state
  isGenerating: false,
  jobId: null,
  progress: 0,
  status: 'idle' as const,
  error: null,
  outputs: null,
};

export const useInstrumentalStore = create<InstrumentalStore>((set, get) => ({
  ...initialState,

  // Form actions
  setLyrics: (lyrics) => set({ lyrics }),
  setGenre: (genre) => set({ genre }),
  setMood: (mood) => set({ mood }),
  setBpm: (bpm) => set({ bpm }),
  setInstruments: (instruments) => set({ instruments }),
  setTitle: (title) => set({ title }),
  setDuration: (duration) => set({ duration }),

  // Generation action
  generateMusic: async () => {
    const state = get();

    // Validation
    if (!state.lyrics.trim()) {
      set({ error: 'Lyrics are required' });
      return;
    }

    if (state.lyrics.length < 10) {
      set({ error: 'Lyrics must be at least 10 characters' });
      return;
    }

    try {
      set({
        isGenerating: true,
        error: null,
        status: 'pending',
        progress: 0,
        outputs: null,
      });

      // Create request
      const request: InstrumentalRequest = {
        lyrics: state.lyrics,
        genre: state.genre,
        mood: state.mood,
        bpm: state.bpm,
        instruments: state.instruments.length > 0 ? state.instruments : null,
        title: state.title,
        duration: state.duration,
      };

      // Start generation
      const response = await generateInstrumental(request);

      set({
        jobId: response.job_id,
        status: response.status,
      });

      // Poll for completion
      await pollInstrumentalStatus(
        response.job_id,
        (statusUpdate) => {
          set({
            status: statusUpdate.status,
            progress: statusUpdate.progress,
            outputs: statusUpdate.outputs,
            error: statusUpdate.error,
          });
        }
      );

      set({
        isGenerating: false,
        status: 'completed',
        progress: 1.0,
      });
    } catch (error) {
      set({
        isGenerating: false,
        status: 'failed',
        error: error instanceof Error ? error.message : 'Generation failed',
      });
    }
  },

  // Reset action
  reset: () => set(initialState),
}));
