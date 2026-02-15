/**
 * Singing Store
 *
 * Manages Singing Synthesis state and operations
 */

import { create } from 'zustand';
import { generateSinging, pollSingingStatus, listSingingModels } from '@/services/singing.service';
import type {
  SingingRequest,
  SingingResponse,
  SingingVoiceModel,
  MelodyMode,
} from '@/types/singing.types';

interface SingingStore {
  // State
  lyrics: string;
  melodyInput: string;
  melodyFile: File | null;
  melodyMode: MelodyMode;
  selectedVoice: string | null;
  tempo: number;
  keyShift: number;
  availableVoices: SingingVoiceModel[];
  isGenerating: boolean;
  progress: number;
  error: string | null;
  result: SingingResponse | null;

  // Actions
  setLyrics: (lyrics: string) => void;
  setMelodyMode: (mode: MelodyMode) => void;
  setMelodyInput: (input: string) => void;
  setMelodyFile: (file: File | null) => void;
  setVoice: (voiceId: string) => void;
  setTempo: (tempo: number) => void;
  setKeyShift: (shift: number) => void;
  loadVoices: () => Promise<void>;
  generate: () => Promise<void>;
  reset: () => void;
}

export const useSingingStore = create<SingingStore>((set, get) => ({
  // Initial state
  lyrics: '',
  melodyInput: '',
  melodyFile: null,
  melodyMode: 'auto',
  selectedVoice: null,
  tempo: 120,
  keyShift: 0,
  availableVoices: [],
  isGenerating: false,
  progress: 0,
  error: null,
  result: null,

  // Actions
  setLyrics: (lyrics) => set({ lyrics }),

  setMelodyMode: (mode) => set({ melodyMode: mode, melodyInput: '', melodyFile: null }),

  setMelodyInput: (input) => set({ melodyInput: input }),

  setMelodyFile: (file) => set({ melodyFile: file }),

  setVoice: (voiceId) => set({ selectedVoice: voiceId }),

  setTempo: (tempo) => set({ tempo }),

  setKeyShift: (shift) => set({ keyShift: shift }),

  loadVoices: async () => {
    try {
      const voices = await listSingingModels();
      set({ availableVoices: voices });

      // Auto-select first voice if none selected
      const { selectedVoice } = get();
      if (!selectedVoice && voices.length > 0) {
        set({ selectedVoice: voices[0].model_id });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load voice models';
      set({ error: errorMessage });
    }
  },

  generate: async () => {
    const { lyrics, melodyMode, melodyInput, melodyFile, selectedVoice, tempo, keyShift } = get();

    // Validation
    if (!lyrics.trim()) {
      set({ error: 'Please enter lyrics to synthesize' });
      return;
    }

    if (!selectedVoice) {
      set({ error: 'Please select a voice model' });
      return;
    }

    if (melodyMode === 'notation' && !melodyInput.trim()) {
      set({ error: 'Please provide melody notation' });
      return;
    }

    if (melodyMode === 'midi' && !melodyFile) {
      set({ error: 'Please upload a MIDI file' });
      return;
    }

    set({ isGenerating: true, progress: 0, error: null, result: null });

    try {
      // Build request
      const request: SingingRequest = {
        lyrics: lyrics.trim(),
        voice_model: selectedVoice,
        tempo,
        key_shift: keyShift,
      };

      // Add melody based on mode
      if (melodyMode === 'auto') {
        request.melody = 'auto';
      } else if (melodyMode === 'notation') {
        request.melody = melodyInput.trim();
      } else if (melodyMode === 'midi' && melodyFile) {
        request.melody_file = melodyFile;
      }

      // Start generation
      const response = await generateSinging(request);

      // Poll for completion
      const finalResult = await pollSingingStatus(response.job_id, (status) => {
        // Update progress based on status
        if (status.status === 'pending') {
          set({ progress: 25 });
        } else if (status.status === 'processing') {
          set({ progress: 60 });
        }
      });

      set({ progress: 100, result: finalResult });

      // Save job ID to localStorage for mixer
      if (finalResult.job_id) {
        const recentJobs = JSON.parse(localStorage.getItem('recent_singing_jobs') || '[]');
        recentJobs.unshift(finalResult.job_id);
        localStorage.setItem('recent_singing_jobs', JSON.stringify(recentJobs.slice(0, 10)));
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Singing synthesis failed';
      set({ error: errorMessage });
    } finally {
      set({ isGenerating: false });
    }
  },

  reset: () =>
    set({
      lyrics: '',
      melodyInput: '',
      melodyFile: null,
      melodyMode: 'auto',
      tempo: 120,
      keyShift: 0,
      isGenerating: false,
      progress: 0,
      error: null,
      result: null,
    }),
}));
