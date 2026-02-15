/**
 * ParametersCard Component
 *
 * TTS generation parameters (speed, pitch, reference audio)
 */

import { useState } from 'react';
import { Card, Button, Textarea } from '@/components/ui';
import type { TTSParameters } from '@/types/tts.types';

interface ParametersCardProps {
  parameters: TTSParameters;
  onSpeedChange: (speed: number) => void;
  onPitchChange: (pitch: number) => void;
  onRefTextChange: (refText: string) => void;
  onReferenceAudioChange: (file: File | undefined) => void;
  showReferenceText?: boolean;
}

export const ParametersCard: React.FC<ParametersCardProps> = ({
  parameters,
  onSpeedChange,
  onPitchChange,
  onRefTextChange,
  onReferenceAudioChange,
  showReferenceText = false,
}) => {
  const [fileName, setFileName] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setFileName(file.name);
      onReferenceAudioChange(file);
    } else {
      setFileName('');
      onReferenceAudioChange(undefined);
    }
  };

  const handleRemoveFile = () => {
    setFileName('');
    onReferenceAudioChange(undefined);
  };

  return (
    <Card className="parameters-card">
      <div className="parameters-card__header">
        <h3>Parameters</h3>
      </div>

      <div className="parameters-card__controls">
        {/* Speed Control */}
        <div className="parameters-card__control">
          <div className="parameters-card__control-header">
            <label>Speed</label>
            <span className="parameters-card__value">{parameters.speed.toFixed(2)}x</span>
          </div>
          <input
            type="range"
            min="0.5"
            max="2.0"
            step="0.1"
            value={parameters.speed}
            onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
            className="parameters-card__slider"
          />
          <div className="parameters-card__slider-labels">
            <span>0.5x</span>
            <span>1.0x</span>
            <span>2.0x</span>
          </div>
        </div>

        {/* Pitch Control */}
        <div className="parameters-card__control">
          <div className="parameters-card__control-header">
            <label>Pitch</label>
            <span className="parameters-card__value">{parameters.pitch.toFixed(2)}x</span>
          </div>
          <input
            type="range"
            min="0.5"
            max="2.0"
            step="0.1"
            value={parameters.pitch}
            onChange={(e) => onPitchChange(parseFloat(e.target.value))}
            className="parameters-card__slider"
          />
          <div className="parameters-card__slider-labels">
            <span>0.5x</span>
            <span>1.0x</span>
            <span>2.0x</span>
          </div>
        </div>

        {/* Reference Text (for IndicF5) */}
        {showReferenceText && (
          <div className="parameters-card__control">
            <Textarea
              label="Reference Text"
              placeholder="Enter reference text for better pronunciation..."
              value={parameters.refText || ''}
              onChange={(e) => onRefTextChange(e.target.value)}
              rows={3}
            />
          </div>
        )}

        {/* Reference Audio Upload */}
        <div className="parameters-card__control">
          <label className="parameters-card__label">Reference Audio (Optional)</label>
          <div className="parameters-card__file-upload">
            {fileName ? (
              <div className="parameters-card__file-info">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M9 18V5l12-2v13M9 13h12"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <span className="parameters-card__file-name">{fileName}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleRemoveFile}
                  className="parameters-card__file-remove"
                >
                  Remove
                </Button>
              </div>
            ) : (
              <label className="parameters-card__file-label">
                <input
                  type="file"
                  accept="audio/*"
                  onChange={handleFileChange}
                  className="parameters-card__file-input"
                />
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                  <path
                    d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <span>Choose audio file</span>
              </label>
            )}
          </div>
          <p className="parameters-card__help-text">
            Upload reference audio to clone voice characteristics
          </p>
        </div>
      </div>
    </Card>
  );
};
