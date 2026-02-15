/**
 * Zustand store for audio mixer state management
 */

import { create } from "zustand";
import { createMix, pollMixStatus } from "../services/mixer.service";
import type { MixRequest, MixResponse, MixParameters } from "../types/mixer.types";

interface MixerStore {
  // State
  selectedTTSJobId: string | null;
  selectedMusicJobId: string | null;
  parameters: MixParameters;
  isMixing: boolean;
  progress: number;
  error: string | null;
  result: MixResponse | null;
  currentStep: "select" | "configure";

  // Actions
  setTTSJob: (jobId: string | null) => void;
  setMusicJob: (jobId: string | null) => void;
  setTTSVolume: (volume: number) => void;
  setMusicVolume: (volume: number) => void;
  setMusicDelay: (delay: number) => void;
  setStep: (step: "select" | "configure") => void;
  mix: () => Promise<void>;
  reset: () => void;
  backToSelect: () => void;
}

export const useMixerStore = create<MixerStore>((set, get) => ({
  // Initial state
  selectedTTSJobId: null,
  selectedMusicJobId: null,
  parameters: {
    tts_volume: 100,
    music_volume: 50,
    music_delay: 0,
  },
  isMixing: false,
  progress: 0,
  error: null,
  result: null,
  currentStep: "select",

  // Set TTS job
  setTTSJob: (jobId: string | null) => {
    set({ selectedTTSJobId: jobId, error: null });
  },

  // Set Music job
  setMusicJob: (jobId: string | null) => {
    set({ selectedMusicJobId: jobId, error: null });
  },

  // Set TTS volume
  setTTSVolume: (volume: number) => {
    set((state) => ({
      parameters: { ...state.parameters, tts_volume: volume },
      error: null,
    }));
  },

  // Set Music volume
  setMusicVolume: (volume: number) => {
    set((state) => ({
      parameters: { ...state.parameters, music_volume: volume },
      error: null,
    }));
  },

  // Set Music delay
  setMusicDelay: (delay: number) => {
    set((state) => ({
      parameters: { ...state.parameters, music_delay: delay },
      error: null,
    }));
  },

  // Set current step
  setStep: (step: "select" | "configure") => {
    set({ currentStep: step, error: null });
  },

  // Mix audio
  mix: async () => {
    const { selectedTTSJobId, selectedMusicJobId, parameters } = get();

    // Validation
    if (!selectedTTSJobId) {
      set({ error: "Please select a TTS job" });
      return;
    }

    if (!selectedMusicJobId) {
      set({ error: "Please select a Music job" });
      return;
    }

    set({
      isMixing: true,
      progress: 0,
      error: null,
      result: null,
    });

    try {
      // Create mix request
      const request: MixRequest = {
        tts_job_id: selectedTTSJobId,
        music_job_id: selectedMusicJobId,
        parameters,
      };

      // Start mixing (returns immediately with job_id)
      const response = await createMix(request);

      // Poll until completion with progress updates
      const finalResult = await pollMixStatus(
        response.job_id,
        (status) => {
          // Update progress based on status
          if (status.status === "pending") {
            set({ progress: 25 });
          } else if (status.status === "processing") {
            const progressValue = status.progress || 60;
            set({ progress: progressValue });
          }
        },
        1000, // Poll every second
        300   // Max 5 minutes
      );

      // Set final result
      set({
        progress: 100,
        result: finalResult,
        isMixing: false,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Mix creation failed";
      set({
        error: errorMessage,
        isMixing: false,
        progress: 0,
      });
    }
  },

  // Reset to select step
  backToSelect: () => {
    set({
      currentStep: "select",
      error: null,
      result: null,
      progress: 0,
    });
  },

  // Reset state completely
  reset: () => {
    set({
      selectedTTSJobId: null,
      selectedMusicJobId: null,
      parameters: {
        tts_volume: 100,
        music_volume: 50,
        music_delay: 0,
      },
      isMixing: false,
      progress: 0,
      error: null,
      result: null,
      currentStep: "select",
    });
  },
}));
