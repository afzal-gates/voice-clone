/**
 * TTS Store
 *
 * Manages Text-to-Speech state and operations
 */

import { create } from 'zustand';
import { generateSpeech, pollTTSStatus, getModels } from '@/services/tts.service';
import type { TTSModel, TTSRequest, TTSResponse, TTSParameters } from '@/types/tts.types';

interface TTSStore {
  // State
  text: string;
  selectedModel: string | null;
  selectedVoiceId: string | null;
  models: TTSModel[];
  parameters: TTSParameters;
  isGenerating: boolean;
  progress: number;
  error: string | null;
  result: TTSResponse | null;

  // Actions
  setText: (text: string) => void;
  setModel: (modelId: string) => void;
  setVoice: (voiceId: string | null) => void;
  setSpeed: (speed: number) => void;
  setPitch: (pitch: number) => void;
  setRefText: (refText: string) => void;
  setReferenceAudio: (file: File | undefined) => void;
  loadModels: () => Promise<void>;
  generate: () => Promise<void>;
  reset: () => void;
}

export const useTTSStore = create<TTSStore>((set, get) => ({
  // Initial state
  text: '',
  selectedModel: null,
  selectedVoiceId: null,
  models: [],
  parameters: {
    speed: 1.0,
    pitch: 1.0,
    refText: undefined,
    referenceAudio: undefined,
  },
  isGenerating: false,
  progress: 0,
  error: null,
  result: null,

  // Actions
  setText: (text) => set({ text }),

  setModel: (modelId) => set({ selectedModel: modelId }),

  setVoice: (voiceId) => set({ selectedVoiceId: voiceId }),

  setSpeed: (speed) =>
    set((state) => ({
      parameters: { ...state.parameters, speed },
    })),

  setPitch: (pitch) =>
    set((state) => ({
      parameters: { ...state.parameters, pitch },
    })),

  setRefText: (refText) =>
    set((state) => ({
      parameters: { ...state.parameters, refText },
    })),

  setReferenceAudio: (file) =>
    set((state) => ({
      parameters: { ...state.parameters, referenceAudio: file },
    })),

  loadModels: async () => {
    try {
      const models = await getModels();
      set({ models });

      // Auto-select first model if none selected
      const { selectedModel } = get();
      if (!selectedModel && models.length > 0) {
        set({ selectedModel: models[0].id });
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load models';
      set({ error: errorMessage });
    }
  },

  generate: async () => {
    const { text, selectedModel, selectedVoiceId, parameters } = get();

    // Validation
    if (!text.trim()) {
      set({ error: 'Please enter text to generate speech' });
      return;
    }

    set({ isGenerating: true, progress: 0, error: null, result: null });

    try {
      // Build request
      const request: TTSRequest = {
        text: text.trim(),
        tts_model: selectedModel || undefined,
        voice_id: selectedVoiceId || undefined,
        speed: parameters.speed,
        pitch: parameters.pitch,
        ref_text: parameters.refText,
        reference_audio: parameters.referenceAudio,
      };

      // Start generation
      const response = await generateSpeech(request);

      // Poll for completion
      const finalResult = await pollTTSStatus(
        response.job_id,
        (status) => {
          // Update progress
          if (status.status === 'pending') {
            set({ progress: 25 });
          } else if (status.status === 'processing') {
            set({ progress: 50 });
          }
        }
      );

      set({ progress: 100, result: finalResult });

      // Save job ID to localStorage for mixer
      if (finalResult.job_id) {
        const recentJobs = JSON.parse(localStorage.getItem('recent_tts_jobs') || '[]');
        recentJobs.unshift(finalResult.job_id);
        localStorage.setItem('recent_tts_jobs', JSON.stringify(recentJobs.slice(0, 10)));
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'TTS generation failed';
      set({ error: errorMessage });
    } finally {
      set({ isGenerating: false });
    }
  },

  reset: () =>
    set({
      text: '',
      selectedVoiceId: null,
      parameters: {
        speed: 1.0,
        pitch: 1.0,
        refText: undefined,
        referenceAudio: undefined,
      },
      isGenerating: false,
      progress: 0,
      error: null,
      result: null,
    }),
}));
