/**
 * Song Generator Store
 *
 * Zustand store for managing complete song generation state
 */

import { create } from 'zustand';
import type {
  SongGeneratorState,
  CompleteSongResponse,
  MusicGenre,
  MusicMood,
  VocalType,
} from '@/types/song.types';
import {
  generateCompleteSong,
  pollSongStatus,
} from '@/services/song.service';

interface SongGeneratorActions {
  // Form actions
  setLyrics: (lyrics: string) => void;
  setGenre: (genre: MusicGenre) => void;
  setMood: (mood: MusicMood) => void;
  setBpm: (bpm: number) => void;
  setInstruments: (instruments: string[]) => void;
  setVocalType: (vocalType: VocalType) => void;
  setLanguage: (language: string) => void;
  setSongTitle: (title: string) => void;
  setArtistName: (name: string) => void;
  setGenerateVideo: (generateVideo: boolean) => void;
  setDuration: (duration: number) => void;
  toggleAdvanced: () => void;

  // Generation actions
  generate: () => Promise<void>;
  reset: () => void;
  updateStatus: (response: CompleteSongResponse) => void;
}

type SongGeneratorStore = SongGeneratorState & SongGeneratorActions;

const initialState: SongGeneratorState = {
  // Form state
  lyrics: '',
  genre: 'pop',
  mood: 'happy',
  bpm: 120,
  instruments: [],
  vocalType: 'ai',
  language: 'en',
  songTitle: 'Untitled Song',
  artistName: 'AI Artist',
  generateVideo: false,
  duration: 30,

  // Job state
  jobId: null,
  status: null,
  outputs: null,
  progress: 0,
  error: null,

  // UI state
  isGenerating: false,
  showAdvanced: false,
};

export const useSongGeneratorStore = create<SongGeneratorStore>((set, get) => ({
  ...initialState,

  // Form actions
  setLyrics: (lyrics) => set({ lyrics }),
  setGenre: (genre) => set({ genre }),
  setMood: (mood) => set({ mood }),
  setBpm: (bpm) => set({ bpm }),
  setInstruments: (instruments) => set({ instruments }),
  setVocalType: (vocalType) => set({ vocalType }),
  setLanguage: (language) => set({ language }),
  setSongTitle: (songTitle) => set({ songTitle }),
  setArtistName: (artistName) => set({ artistName }),
  setGenerateVideo: (generateVideo) => set({ generateVideo }),
  setDuration: (duration) => set({ duration }),
  toggleAdvanced: () => set((state) => ({ showAdvanced: !state.showAdvanced })),

  // Generation actions
  generate: async () => {
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
        jobId: null,
        status: null,
        outputs: null,
        progress: 0,
      });

      // Start generation
      const response = await generateCompleteSong({
        lyrics: state.lyrics,
        genre: state.genre,
        mood: state.mood,
        bpm: state.bpm,
        instruments: state.instruments.length > 0 ? state.instruments : undefined,
        vocal_type: state.vocalType,
        language: state.language,
        song_title: state.songTitle,
        artist_name: state.artistName,
        generate_video: state.generateVideo,
        duration: state.duration,
      });

      set({
        jobId: response.job_id,
        status: response.status,
      });

      // Poll for completion
      const finalResponse = await pollSongStatus(
        response.job_id,
        (statusUpdate) => {
          set({
            status: statusUpdate.status,
            progress: statusUpdate.progress,
            outputs: statusUpdate.outputs || null,
          });
        }
      );

      set({
        status: finalResponse.status,
        outputs: finalResponse.outputs || null,
        progress: finalResponse.progress,
        isGenerating: false,
      });
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : 'Song generation failed';
      set({
        error: errorMessage,
        isGenerating: false,
        status: 'failed',
      });
    }
  },

  reset: () => set({ ...initialState }),

  updateStatus: (response) =>
    set({
      status: response.status,
      outputs: response.outputs || null,
      progress: response.progress,
      error: response.error || null,
    }),
}));
