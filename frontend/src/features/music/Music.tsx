/**
 * Music Generation Feature - Main Component
 *
 * Generates music from text prompts using AudioCraft MusicGen
 */

import React, { useState } from "react";
import { useMusicStore } from "../../store/musicStore";
import { downloadMusic } from "../../services/music.service";
import { MUSIC_STYLES } from "../../types/music.types";
import type { MusicStyle } from "../../types/music.types";

export const Music: React.FC = () => {
  const {
    prompt,
    setPrompt,
    selectedStyle,
    setStyle,
    parameters,
    setDuration,
    setReferenceAudio,
    isGenerating,
    progress,
    error,
    result,
    generate,
    reset,
  } = useMusicStore();

  const [refAudioFile, setRefAudioFile] = useState<File | undefined>();

  const handleReferenceAudioChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setRefAudioFile(file);
    setReferenceAudio(file);
  };

  const handleGenerate = async () => {
    await generate();
  };

  return (
    <div style={{ maxWidth: "800px", margin: "0 auto", padding: "20px" }}>
      <h1>Music Generation</h1>
      <p style={{ color: "#666", marginBottom: "30px" }}>
        Generate music from text descriptions using AI
      </p>

      {/* Prompt Input */}
      <div style={{ marginBottom: "20px" }}>
        <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
          Music Description *
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the music you want to generate (e.g., 'upbeat electronic dance music with synthesizers')"
          rows={4}
          style={{
            width: "100%",
            padding: "12px",
            fontSize: "14px",
            border: "1px solid #ddd",
            borderRadius: "4px",
            fontFamily: "inherit",
          }}
          disabled={isGenerating}
        />
        <div style={{ fontSize: "12px", color: "#666", marginTop: "4px" }}>
          {prompt.length}/500 characters
        </div>
      </div>

      {/* Style Selector */}
      <div style={{ marginBottom: "20px" }}>
        <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
          Genre/Style (Optional)
        </label>
        <select
          value={selectedStyle || ""}
          onChange={(e) => setStyle((e.target.value as MusicStyle) || null)}
          style={{
            width: "100%",
            padding: "12px",
            fontSize: "14px",
            border: "1px solid #ddd",
            borderRadius: "4px",
          }}
          disabled={isGenerating}
        >
          <option value="">No style (use prompt only)</option>
          {MUSIC_STYLES.map((style) => (
            <option key={style.value} value={style.value}>
              {style.label} - {style.description}
            </option>
          ))}
        </select>
      </div>

      {/* Duration Slider */}
      <div style={{ marginBottom: "20px" }}>
        <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
          Duration: {parameters.duration} seconds
        </label>
        <input
          type="range"
          min="5"
          max="30"
          step="1"
          value={parameters.duration}
          onChange={(e) => setDuration(Number(e.target.value))}
          style={{ width: "100%" }}
          disabled={isGenerating}
        />
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "12px", color: "#666" }}>
          <span>5s</span>
          <span>30s</span>
        </div>
      </div>

      {/* Reference Audio Upload */}
      <div style={{ marginBottom: "20px" }}>
        <label style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>
          Reference Audio (Optional)
        </label>
        <input
          type="file"
          accept="audio/*"
          onChange={handleReferenceAudioChange}
          style={{
            width: "100%",
            padding: "12px",
            fontSize: "14px",
            border: "1px solid #ddd",
            borderRadius: "4px",
          }}
          disabled={isGenerating}
        />
        {refAudioFile && (
          <div style={{ fontSize: "12px", color: "#666", marginTop: "4px" }}>
            Selected: {refAudioFile.name}
          </div>
        )}
        <div style={{ fontSize: "12px", color: "#666", marginTop: "4px" }}>
          Upload an audio file to guide the melody and style
        </div>
      </div>

      {/* Generate Button */}
      <div style={{ marginBottom: "30px" }}>
        <button
          onClick={handleGenerate}
          disabled={isGenerating || !prompt.trim()}
          style={{
            width: "100%",
            padding: "14px 24px",
            fontSize: "16px",
            fontWeight: "bold",
            color: "#fff",
            backgroundColor: isGenerating || !prompt.trim() ? "#ccc" : "#007bff",
            border: "none",
            borderRadius: "4px",
            cursor: isGenerating || !prompt.trim() ? "not-allowed" : "pointer",
          }}
        >
          {isGenerating ? "Generating Music..." : "Generate Music"}
        </button>
      </div>

      {/* Progress Bar */}
      {isGenerating && (
        <div style={{ marginBottom: "20px" }}>
          <div style={{ marginBottom: "8px", fontWeight: "bold" }}>
            Progress: {progress}%
          </div>
          <div
            style={{
              width: "100%",
              height: "20px",
              backgroundColor: "#f0f0f0",
              borderRadius: "10px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${progress}%`,
                height: "100%",
                backgroundColor: "#007bff",
                transition: "width 0.3s ease",
              }}
            />
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div
          style={{
            padding: "16px",
            marginBottom: "20px",
            backgroundColor: "#fee",
            border: "1px solid #fcc",
            borderRadius: "4px",
            color: "#c33",
          }}
        >
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Result */}
      {result && result.status === "completed" && result.output_file && (
        <div
          style={{
            padding: "20px",
            backgroundColor: "#f9f9f9",
            border: "1px solid #ddd",
            borderRadius: "4px",
          }}
        >
          <h3 style={{ marginTop: 0 }}>Music Generated!</h3>
          <p style={{ color: "#666" }}>
            Duration: {result.duration?.toFixed(1)}s
          </p>

          {/* Audio Player */}
          <audio
            controls
            style={{ width: "100%", marginBottom: "16px" }}
            src={downloadMusic(result.job_id, "wav")}
          />

          {/* Download Buttons */}
          <div style={{ display: "flex", gap: "10px" }}>
            <a
              href={downloadMusic(result.job_id, "wav")}
              download
              style={{
                flex: 1,
                padding: "10px",
                textAlign: "center",
                backgroundColor: "#28a745",
                color: "#fff",
                textDecoration: "none",
                borderRadius: "4px",
                fontWeight: "bold",
              }}
            >
              Download WAV
            </a>
            <a
              href={downloadMusic(result.job_id, "mp3")}
              download
              style={{
                flex: 1,
                padding: "10px",
                textAlign: "center",
                backgroundColor: "#17a2b8",
                color: "#fff",
                textDecoration: "none",
                borderRadius: "4px",
                fontWeight: "bold",
              }}
            >
              Download MP3
            </a>
          </div>

          {/* Reset Button */}
          <button
            onClick={reset}
            style={{
              width: "100%",
              marginTop: "16px",
              padding: "10px",
              fontSize: "14px",
              color: "#666",
              backgroundColor: "#fff",
              border: "1px solid #ddd",
              borderRadius: "4px",
              cursor: "pointer",
            }}
          >
            Generate Another
          </button>
        </div>
      )}
    </div>
  );
};
