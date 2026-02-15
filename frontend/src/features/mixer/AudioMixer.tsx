/**
 * Audio Mixer Feature - Main Component
 *
 * Mixes TTS output with Music generation for background music
 */

import React, { useState, useEffect } from "react";
import { useMixerStore } from "../../store/mixerStore";
import { downloadMix } from "../../services/mixer.service";
import { getTTSStatus } from "../../services/tts.service";
import { getMusicStatus } from "../../services/music.service";

interface JobOption {
  job_id: string;
  label: string;
  type: "tts" | "music";
}

export const AudioMixer: React.FC = () => {
  const {
    selectedTTSJobId,
    selectedMusicJobId,
    parameters,
    isMixing,
    progress,
    error,
    result,
    currentStep,
    setTTSJob,
    setMusicJob,
    setTTSVolume,
    setMusicVolume,
    setMusicDelay,
    setStep,
    mix,
    reset,
    backToSelect,
  } = useMixerStore();

  const [ttsJobs, setTtsJobs] = useState<JobOption[]>([]);
  const [musicJobs, setMusicJobs] = useState<JobOption[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);

  // Load recent TTS and Music jobs
  useEffect(() => {
    loadRecentJobs();
  }, []);

  const loadRecentJobs = async () => {
    setLoadingJobs(true);
    try {
      // Get TTS jobs from localStorage (recent generations)
      const ttsJobIds = getRecentJobIds("tts");
      const musicJobIds = getRecentJobIds("music");

      // Fetch job details
      const ttsJobPromises = ttsJobIds.map(async (id) => {
        try {
          const job = await getTTSStatus(id);
          if (job.status === "completed" && job.output_file) {
            return {
              job_id: id,
              label: `TTS Job ${id.substring(0, 8)} (${new Date().toLocaleDateString()})`,
              type: "tts" as const,
            };
          }
        } catch (err) {
          console.error(`Failed to load TTS job ${id}:`, err);
        }
        return null;
      });

      const musicJobPromises = musicJobIds.map(async (id) => {
        try {
          const job = await getMusicStatus(id);
          if (job.status === "completed" && job.output_file) {
            return {
              job_id: id,
              label: `Music Job ${id.substring(0, 8)} (${Math.round(job.duration || 0)}s)`,
              type: "music" as const,
            };
          }
        } catch (err) {
          console.error(`Failed to load Music job ${id}:`, err);
        }
        return null;
      });

      const ttsResults = await Promise.all(ttsJobPromises);
      const musicResults = await Promise.all(musicJobPromises);

      setTtsJobs(ttsResults.filter((job) => job !== null) as JobOption[]);
      setMusicJobs(musicResults.filter((job) => job !== null) as JobOption[]);
    } catch (err) {
      console.error("Failed to load recent jobs:", err);
    } finally {
      setLoadingJobs(false);
    }
  };

  // Helper to get recent job IDs from localStorage
  const getRecentJobIds = (type: "tts" | "music"): string[] => {
    const key = `recent_${type}_jobs`;
    const stored = localStorage.getItem(key);
    if (stored) {
      try {
        return JSON.parse(stored).slice(0, 10); // Last 10 jobs
      } catch {
        return [];
      }
    }
    return [];
  };

  const handleNext = () => {
    if (!selectedTTSJobId) {
      alert("Please select a TTS job");
      return;
    }
    if (!selectedMusicJobId) {
      alert("Please select a Music job");
      return;
    }
    setStep("configure");
  };

  const handleMix = async () => {
    await mix();
  };

  const handleDownload = (format: "wav" | "mp3") => {
    if (result?.job_id) {
      const url = downloadMix(result.job_id, format);
      const link = document.createElement("a");
      link.href = url;
      link.download = `mixed_audio_${result.job_id.substring(0, 8)}.${format}`;
      link.click();
    }
  };

  const handleReset = () => {
    reset();
    loadRecentJobs();
  };

  // Step 1: Select Jobs
  if (currentStep === "select") {
    return (
      <div style={{ maxWidth: "800px", margin: "0 auto", padding: "20px" }}>
        <h1>Audio Mixer</h1>
        <p style={{ color: "#666", marginBottom: "30px" }}>
          Mix TTS output with background music
        </p>

        {loadingJobs ? (
          <div style={{ textAlign: "center", padding: "40px" }}>
            <p>Loading recent jobs...</p>
          </div>
        ) : (
          <>
            {/* Step 1: Select TTS Job */}
            <div style={{ marginBottom: "30px" }}>
              <h2 style={{ fontSize: "18px", marginBottom: "15px" }}>
                Step 1: Select TTS Output
              </h2>
              {ttsJobs.length === 0 ? (
                <div
                  style={{
                    padding: "20px",
                    backgroundColor: "#f9f9f9",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                    textAlign: "center",
                    color: "#666",
                  }}
                >
                  No completed TTS jobs found. Please generate a TTS output first.
                </div>
              ) : (
                <select
                  value={selectedTTSJobId || ""}
                  onChange={(e) => setTTSJob(e.target.value || null)}
                  style={{
                    width: "100%",
                    padding: "12px",
                    fontSize: "14px",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                  }}
                >
                  <option value="">Select a TTS job...</option>
                  {ttsJobs.map((job) => (
                    <option key={job.job_id} value={job.job_id}>
                      {job.label}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Step 2: Select Music Job */}
            <div style={{ marginBottom: "30px" }}>
              <h2 style={{ fontSize: "18px", marginBottom: "15px" }}>
                Step 2: Select Background Music
              </h2>
              {musicJobs.length === 0 ? (
                <div
                  style={{
                    padding: "20px",
                    backgroundColor: "#f9f9f9",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                    textAlign: "center",
                    color: "#666",
                  }}
                >
                  No completed Music jobs found. Please generate music first.
                </div>
              ) : (
                <select
                  value={selectedMusicJobId || ""}
                  onChange={(e) => setMusicJob(e.target.value || null)}
                  style={{
                    width: "100%",
                    padding: "12px",
                    fontSize: "14px",
                    border: "1px solid #ddd",
                    borderRadius: "4px",
                  }}
                >
                  <option value="">Select a music job...</option>
                  {musicJobs.map((job) => (
                    <option key={job.job_id} value={job.job_id}>
                      {job.label}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Next Button */}
            <div style={{ display: "flex", gap: "10px" }}>
              <button
                onClick={handleNext}
                disabled={!selectedTTSJobId || !selectedMusicJobId}
                style={{
                  flex: 1,
                  padding: "12px 24px",
                  fontSize: "16px",
                  fontWeight: "bold",
                  backgroundColor:
                    selectedTTSJobId && selectedMusicJobId ? "#4CAF50" : "#ccc",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor:
                    selectedTTSJobId && selectedMusicJobId ? "pointer" : "not-allowed",
                }}
              >
                Next: Configure Mix
              </button>
              <button
                onClick={loadRecentJobs}
                style={{
                  padding: "12px 24px",
                  fontSize: "16px",
                  backgroundColor: "#fff",
                  color: "#333",
                  border: "1px solid #ddd",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                Refresh Jobs
              </button>
            </div>
          </>
        )}
      </div>
    );
  }

  // Step 2: Configure and Mix
  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "20px" }}>
      <h1>Audio Mixer - Configure</h1>
      <p style={{ color: "#666", marginBottom: "30px" }}>
        Adjust volume levels and timing
      </p>

      {/* TTS Volume */}
      <div style={{ marginBottom: "20px" }}>
        <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
          Voice Volume: {parameters.tts_volume}%
        </label>
        <input
          type="range"
          min="0"
          max="100"
          step="1"
          value={parameters.tts_volume}
          onChange={(e) => setTTSVolume(Number(e.target.value))}
          style={{ width: "100%" }}
          disabled={isMixing}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "12px",
            color: "#666",
          }}
        >
          <span>0%</span>
          <span>100%</span>
        </div>
      </div>

      {/* Music Volume */}
      <div style={{ marginBottom: "20px" }}>
        <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
          Music Volume: {parameters.music_volume}%
        </label>
        <input
          type="range"
          min="0"
          max="100"
          step="1"
          value={parameters.music_volume}
          onChange={(e) => setMusicVolume(Number(e.target.value))}
          style={{ width: "100%" }}
          disabled={isMixing}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "12px",
            color: "#666",
          }}
        >
          <span>0%</span>
          <span>100%</span>
        </div>
      </div>

      {/* Music Delay */}
      <div style={{ marginBottom: "30px" }}>
        <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
          Music Start Delay: {parameters.music_delay.toFixed(1)}s
        </label>
        <input
          type="range"
          min="0"
          max="5"
          step="0.1"
          value={parameters.music_delay}
          onChange={(e) => setMusicDelay(Number(e.target.value))}
          style={{ width: "100%" }}
          disabled={isMixing}
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "12px",
            color: "#666",
          }}
        >
          <span>0s</span>
          <span>5s</span>
        </div>
        <div style={{ fontSize: "12px", color: "#666", marginTop: "4px" }}>
          Delay music start for voice clarity
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div
          style={{
            padding: "12px",
            backgroundColor: "#fee",
            color: "#c33",
            borderRadius: "4px",
            marginBottom: "20px",
            border: "1px solid #fcc",
          }}
        >
          {error}
        </div>
      )}

      {/* Progress Bar */}
      {isMixing && (
        <div style={{ marginBottom: "20px" }}>
          <div style={{ marginBottom: "8px", fontSize: "14px", color: "#666" }}>
            Mixing audio... {progress}%
          </div>
          <div
            style={{
              width: "100%",
              height: "8px",
              backgroundColor: "#e0e0e0",
              borderRadius: "4px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${progress}%`,
                height: "100%",
                backgroundColor: "#4CAF50",
                transition: "width 0.3s ease",
              }}
            />
          </div>
        </div>
      )}

      {/* Result Audio Player */}
      {result && result.output_file && (
        <div
          style={{
            marginBottom: "20px",
            padding: "20px",
            backgroundColor: "#f0f9f0",
            border: "1px solid #c3e6c3",
            borderRadius: "4px",
          }}
        >
          <h3 style={{ fontSize: "16px", marginBottom: "15px", color: "#2e7d32" }}>
            Mix Complete!
          </h3>
          <audio
            controls
            style={{ width: "100%", marginBottom: "15px" }}
            src={`/api/jobs/${result.job_id}/audio`}
          />
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={() => handleDownload("wav")}
              style={{
                flex: 1,
                padding: "10px",
                fontSize: "14px",
                backgroundColor: "#4CAF50",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              Download WAV
            </button>
            <button
              onClick={() => handleDownload("mp3")}
              style={{
                flex: 1,
                padding: "10px",
                fontSize: "14px",
                backgroundColor: "#2196F3",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              Download MP3
            </button>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div style={{ display: "flex", gap: "10px" }}>
        {!result && (
          <>
            <button
              onClick={backToSelect}
              disabled={isMixing}
              style={{
                padding: "12px 24px",
                fontSize: "16px",
                backgroundColor: "#fff",
                color: "#333",
                border: "1px solid #ddd",
                borderRadius: "4px",
                cursor: isMixing ? "not-allowed" : "pointer",
              }}
            >
              Back
            </button>
            <button
              onClick={handleMix}
              disabled={isMixing}
              style={{
                flex: 1,
                padding: "12px 24px",
                fontSize: "16px",
                fontWeight: "bold",
                backgroundColor: isMixing ? "#ccc" : "#4CAF50",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: isMixing ? "not-allowed" : "pointer",
              }}
            >
              {isMixing ? "Mixing..." : "Mix Audio"}
            </button>
          </>
        )}
        {result && (
          <>
            <button
              onClick={backToSelect}
              style={{
                flex: 1,
                padding: "12px 24px",
                fontSize: "16px",
                backgroundColor: "#fff",
                color: "#333",
                border: "1px solid #ddd",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              Mix Another
            </button>
            <button
              onClick={handleReset}
              style={{
                flex: 1,
                padding: "12px 24px",
                fontSize: "16px",
                backgroundColor: "#f44336",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              Start Over
            </button>
          </>
        )}
      </div>
    </div>
  );
};
