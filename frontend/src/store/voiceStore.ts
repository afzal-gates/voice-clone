/**
 * Voice Store
 *
 * Manages voice library state and operations
 */

import { create } from 'zustand';
import {
  getVoices,
  getVoicePreviewUrl,
  deleteVoice as deleteVoiceAPI,
  uploadVoice as uploadVoiceAPI,
} from '@/services/tts.service';
import type { VoiceProfile } from '@/types/tts.types';

interface VoiceStore {
  // State
  voices: VoiceProfile[];
  selectedVoiceId: string | null;
  playingVoiceId: string | null;
  previewAudio: HTMLAudioElement | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  loadVoices: () => Promise<void>;
  selectVoice: (voiceId: string) => void;
  playPreview: (voiceId: string) => void;
  stopPreview: () => void;
  uploadVoice: (audioFile: File, name: string, description?: string) => Promise<VoiceProfile>;
  deleteVoice: (voiceId: string) => Promise<void>;
}

export const useVoiceStore = create<VoiceStore>((set, get) => ({
  // Initial state
  voices: [],
  selectedVoiceId: null,
  playingVoiceId: null,
  previewAudio: null,
  isLoading: false,
  error: null,

  // Actions
  loadVoices: async () => {
    set({ isLoading: true, error: null });

    try {
      const voices = await getVoices();
      set({ voices, isLoading: false });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load voices';
      set({ error: errorMessage, isLoading: false });
    }
  },

  selectVoice: (voiceId) => {
    set({ selectedVoiceId: voiceId });
  },

  playPreview: (voiceId) => {
    const { previewAudio, playingVoiceId } = get();

    // Stop current preview if playing
    if (previewAudio) {
      previewAudio.pause();
      previewAudio.currentTime = 0;
    }

    // If same voice, just stop
    if (playingVoiceId === voiceId && previewAudio) {
      set({ previewAudio: null, playingVoiceId: null });
      return;
    }

    // Create new audio element
    const audio = new Audio(getVoicePreviewUrl(voiceId));

    audio.addEventListener('ended', () => {
      set({ previewAudio: null, playingVoiceId: null });
    });

    audio.addEventListener('error', () => {
      set({ previewAudio: null, playingVoiceId: null, error: 'Failed to play preview' });
    });

    audio.play();
    set({ previewAudio: audio, playingVoiceId: voiceId });
  },

  stopPreview: () => {
    const { previewAudio } = get();
    if (previewAudio) {
      previewAudio.pause();
      previewAudio.currentTime = 0;
    }
    set({ previewAudio: null, playingVoiceId: null });
  },

  uploadVoice: async (audioFile, name, description) => {
    try {
      const newVoice = await uploadVoiceAPI(audioFile, name, description);

      // Add to store
      const { voices } = get();
      set({ voices: [newVoice, ...voices] });

      return newVoice;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload voice';
      set({ error: errorMessage });
      throw err;
    }
  },

  deleteVoice: async (voiceId) => {
    try {
      await deleteVoiceAPI(voiceId);

      // Remove from store
      const { voices } = get();
      const updatedVoices = voices.filter((v) => v.id !== voiceId);
      set({ voices: updatedVoices });

      // Clear selection if deleted voice was selected
      const { selectedVoiceId } = get();
      if (selectedVoiceId === voiceId) {
        set({ selectedVoiceId: null });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to delete voice';
      set({ error: errorMessage });
      throw err;
    }
  },
}));
