/**
 * Audio Meters Component
 *
 * Displays input and output audio levels
 */

import React from 'react';
import type { AudioStatus } from '@/types/realtime.types';

interface AudioMetersProps {
  audioStatus: AudioStatus;
}

export const AudioMeters: React.FC<AudioMetersProps> = ({ audioStatus }) => {
  const formatLatency = (ms: number) => {
    return `${Math.round(ms)}ms`;
  };

  const getLevelColor = (level: number) => {
    if (level < 0.3) return '#22c55e'; // green
    if (level < 0.7) return '#eab308'; // yellow
    return '#ef4444'; // red
  };

  return (
    <div className="audio-meters">
      <div className="audio-meters__meter">
        <div className="audio-meters__header">
          <span className="audio-meters__label">Input Level</span>
          <span className="audio-meters__value">
            {Math.round(audioStatus.input_level * 100)}%
          </span>
        </div>
        <div className="audio-meters__bar">
          <div
            className="audio-meters__fill"
            style={{
              width: `${audioStatus.input_level * 100}%`,
              backgroundColor: getLevelColor(audioStatus.input_level),
            }}
          />
        </div>
      </div>

      <div className="audio-meters__meter">
        <div className="audio-meters__header">
          <span className="audio-meters__label">Output Level</span>
          <span className="audio-meters__value">
            {Math.round(audioStatus.output_level * 100)}%
          </span>
        </div>
        <div className="audio-meters__bar">
          <div
            className="audio-meters__fill"
            style={{
              width: `${audioStatus.output_level * 100}%`,
              backgroundColor: getLevelColor(audioStatus.output_level),
            }}
          />
        </div>
      </div>

      <div className="audio-meters__stats">
        <div className="audio-meters__stat">
          <span className="audio-meters__stat-label">Latency:</span>
          <span className="audio-meters__stat-value">
            {formatLatency(audioStatus.latency_ms)}
          </span>
        </div>
        <div className="audio-meters__stat">
          <span className="audio-meters__stat-label">Processing:</span>
          <span className="audio-meters__stat-value">
            {formatLatency(audioStatus.processing_time_ms)}
          </span>
        </div>
      </div>
    </div>
  );
};
