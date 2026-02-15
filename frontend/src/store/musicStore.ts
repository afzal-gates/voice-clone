/**
 * Zustand store for music generation state management
 */

import { create } from "zustand";
import { generateMusic, pollMusicStatus } from "../services/music.service";
import type {
  MusicRequest,
  MusicResponse,
  MusicParameters,
  MusicStyle,
} from "../types/music.types";

interface MusicStore {
  // State
  prompt: string;
  selectedStyle: MusicStyle | null;
  parameters: MusicParameters;
  isGenerating: boolean;
  progress: number;
  error: string | null;
  result: MusicResponse | null;

  // Actions
  setPrompt: (prompt: string) => void;
  setStyle: (style: MusicStyle | null) => void;
  setDuration: (duration: number) => void;
  setReferenceAudio: (file: File | undefined) => void;
  generate: () => Promise<void>;
  reset: () => void;
}

export const useMusicStore = create<MusicStore>((set, get) => ({
  // Initial state
  prompt: "",
  selectedStyle: null,
  parameters: {
    duration: 10.0,
    style: undefined,
    referenceAudio: undefined,
  },
  isGenerating: false,
  progress: 0,
  error: null,
  result: null,

  // Set prompt
  setPrompt: (prompt: string) => {
    set({ prompt, error: null });
  },

  // Set style
  setStyle: (style: MusicStyle | null) => {
    set((state) => ({
      selectedStyle: style,
      parameters: { ...state.parameters, style: style || undefined },
      error: null,
    }));
  },

  // Set duration
  setDuration: (duration: number) => {
    set((state) => ({
      parameters: { ...state.parameters, duration },
      error: null,
    }));
  },

  // Set reference audio
  setReferenceAudio: (file: File | undefined) => {
    set((state) => ({
      parameters: { ...state.parameters, referenceAudio: file },
      error: null,
    }));
  },

  // Generate music
  generate: async () => {
    const { prompt, parameters } = get();

    // Validation
    if (!prompt.trim()) {
      set({ error: "Please enter a music description" });
      return;
    }

    if (prompt.length > 500) {
      set({ error: "Prompt must be 500 characters or less" });
      return;
    }

    set({
      isGenerating: true,
      progress: 0,
      error: null,
      result: null,
    });

    try {
      // Create request
      const request: MusicRequest = {
        prompt: prompt.trim(),
        duration: parameters.duration,
        style: parameters.style,
        reference_audio: parameters.referenceAudio,
      };

      // Generate music (returns immediately with job_id)
      const response = await generateMusic(request);

      // Poll until completion with progress updates
      const finalResult = await pollMusicStatus(
        response.job_id,
        (status) => {
          // Update progress based on status
          if (status.status === "pending") {
            set({ progress: 25 });
          } else if (status.status === "processing") {
            set({ progress: 60 });
          }
        },
        1000, // Poll every second
        300   // Max 5 minutes
      );

      // Set final result
      set({
        progress: 100,
        result: finalResult,
        isGenerating: false,
      });

      // Save job ID to localStorage for mixer
      if (finalResult.job_id) {
        const recentJobs = JSON.parse(localStorage.getItem('recent_music_jobs') || '[]');
        recentJobs.unshift(finalResult.job_id);
        localStorage.setItem('recent_music_jobs', JSON.stringify(recentJobs.slice(0, 10)));
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Music generation failed";
      set({
        error: errorMessage,
        isGenerating: false,
        progress: 0,
      });
    }
  },

  // Reset state
  reset: () => {
    set({
      prompt: "",
      selectedStyle: null,
      parameters: {
        duration: 10.0,
        style: undefined,
        referenceAudio: undefined,
      },
      isGenerating: false,
      progress: 0,
      error: null,
      result: null,
    });
  },
}));
