/**
 * API service for music generation
 */

import type { MusicRequest, MusicResponse } from "../types/music.types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Generate music from a text prompt
 */
export const generateMusic = async (request: MusicRequest): Promise<MusicResponse> => {
  const formData = new FormData();
  formData.append("prompt", request.prompt);
  formData.append("duration", request.duration.toString());

  if (request.style) {
    formData.append("style", request.style);
  }

  if (request.reference_audio) {
    formData.append("reference_audio", request.reference_audio);
  }

  const response = await fetch(`${API_BASE}/api/music`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Music generation failed");
  }

  return response.json();
};

/**
 * Get music generation job status
 */
export const getMusicStatus = async (jobId: string): Promise<MusicResponse> => {
  const response = await fetch(`${API_BASE}/api/music/${jobId}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to get music status");
  }

  return response.json();
};

/**
 * Poll music generation status until completion
 */
export const pollMusicStatus = async (
  jobId: string,
  onProgress?: (status: MusicResponse) => void,
  pollInterval: number = 1000,
  maxAttempts: number = 300
): Promise<MusicResponse> => {
  let attempts = 0;

  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getMusicStatus(jobId);

        if (onProgress) {
          onProgress(status);
        }

        if (status.status === "completed") {
          resolve(status);
          return;
        }

        if (status.status === "failed") {
          reject(new Error(status.error || "Music generation failed"));
          return;
        }

        attempts++;
        if (attempts >= maxAttempts) {
          reject(new Error("Music generation timeout"));
          return;
        }

        setTimeout(poll, pollInterval);
      } catch (error) {
        reject(error);
      }
    };

    poll();
  });
};

/**
 * Download music file
 */
export const downloadMusic = (jobId: string, format: "wav" | "mp3" = "wav"): string => {
  return `${API_BASE}/api/jobs/${jobId}/download?format=${format}`;
};
