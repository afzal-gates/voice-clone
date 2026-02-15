/**
 * API service for audio mixing
 */

import type { MixRequest, MixResponse } from "../types/mixer.types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Create a mix of TTS and Music
 */
export const createMix = async (request: MixRequest): Promise<MixResponse> => {
  const response = await fetch(`${API_BASE}/api/mixer/mix`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Mix creation failed" }));
    throw new Error(error.detail || "Mix creation failed");
  }

  return response.json();
};

/**
 * Get mix job status
 */
export const getMixStatus = async (jobId: string): Promise<MixResponse> => {
  const response = await fetch(`${API_BASE}/api/mixer/mix/${jobId}`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to get mix status" }));
    throw new Error(error.detail || "Failed to get mix status");
  }

  return response.json();
};

/**
 * Poll mix status until completion
 */
export const pollMixStatus = async (
  jobId: string,
  onProgress?: (status: MixResponse) => void,
  pollInterval: number = 1000,
  maxAttempts: number = 300
): Promise<MixResponse> => {
  let attempts = 0;

  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getMixStatus(jobId);

        if (onProgress) {
          onProgress(status);
        }

        if (status.status === "completed") {
          resolve(status);
          return;
        }

        if (status.status === "failed") {
          reject(new Error(status.error || "Mix generation failed"));
          return;
        }

        attempts++;
        if (attempts >= maxAttempts) {
          reject(new Error("Mix generation timeout"));
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
 * Download mixed audio file
 */
export const downloadMix = (jobId: string, format: "wav" | "mp3" = "wav"): string => {
  return `${API_BASE}/api/jobs/${jobId}/download?format=${format}`;
};
