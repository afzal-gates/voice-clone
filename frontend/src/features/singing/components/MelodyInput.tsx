/**
 * Melody Input Component
 *
 * Mode selector and inputs for auto/notation/MIDI melody
 */

import React, { useRef } from 'react';
import { Card, Button, Input } from '@/components/ui';
import type { MelodyMode } from '@/types/singing.types';
import { EXAMPLE_NOTATION, SINGING_HELP_TEXT } from '@/types/singing.types';

interface MelodyInputProps {
  mode: MelodyMode;
  notationInput: string;
  midiFile: File | null;
  onModeChange: (mode: MelodyMode) => void;
  onNotationChange: (notation: string) => void;
  onMidiFileChange: (file: File | null) => void;
  disabled?: boolean;
}

export const MelodyInput: React.FC<MelodyInputProps> = ({
  mode,
  notationInput,
  midiFile,
  onModeChange,
  onNotationChange,
  onMidiFileChange,
  disabled,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.name.endsWith('.mid') || file.name.endsWith('.midi')) {
        onMidiFileChange(file);
      } else {
        alert('Please upload a valid MIDI file (.mid or .midi)');
      }
    }
  };

  const handleExampleClick = (exampleKey: string) => {
    const notation = EXAMPLE_NOTATION[exampleKey as keyof typeof EXAMPLE_NOTATION];
    onNotationChange(notation);
  };

  const handleRemoveFile = () => {
    onMidiFileChange(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Card className="melody-input">
      <div className="melody-input__header">
        <h3>Step 2: Configure Melody</h3>
      </div>

      {/* Mode Selection */}
      <div className="melody-input__modes">
        <label className="melody-input__mode">
          <input
            type="radio"
            name="melody-mode"
            value="auto"
            checked={mode === 'auto'}
            onChange={() => onModeChange('auto')}
            disabled={disabled}
          />
          <div className="melody-input__mode-content">
            <strong>Auto-Generate</strong>
            <span>{SINGING_HELP_TEXT.melodyAuto}</span>
          </div>
        </label>

        <label className="melody-input__mode">
          <input
            type="radio"
            name="melody-mode"
            value="notation"
            checked={mode === 'notation'}
            onChange={() => onModeChange('notation')}
            disabled={disabled}
          />
          <div className="melody-input__mode-content">
            <strong>Notation Input</strong>
            <span>{SINGING_HELP_TEXT.melodyNotation}</span>
          </div>
        </label>

        <label className="melody-input__mode">
          <input
            type="radio"
            name="melody-mode"
            value="midi"
            checked={mode === 'midi'}
            onChange={() => onModeChange('midi')}
            disabled={disabled}
          />
          <div className="melody-input__mode-content">
            <strong>MIDI File</strong>
            <span>{SINGING_HELP_TEXT.melodyMidi}</span>
          </div>
        </label>
      </div>

      {/* Notation Input */}
      {mode === 'notation' && (
        <div className="melody-input__notation">
          <Input
            type="text"
            value={notationInput}
            onChange={(e) => onNotationChange(e.target.value)}
            placeholder="C4:1.0 D4:0.5 E4:0.5 F4:1.0..."
            disabled={disabled}
          />
          <div className="melody-input__examples">
            <span className="melody-input__examples-label">Examples:</span>
            {Object.keys(EXAMPLE_NOTATION).map((key) => (
              <Button
                key={key}
                variant="secondary"
                size="sm"
                onClick={() => handleExampleClick(key)}
                disabled={disabled}
              >
                {key}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* MIDI File Upload */}
      {mode === 'midi' && (
        <div className="melody-input__file">
          <input
            ref={fileInputRef}
            type="file"
            accept=".mid,.midi"
            onChange={handleFileChange}
            disabled={disabled}
            style={{ display: 'none' }}
          />
          {!midiFile ? (
            <Button
              variant="secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={disabled}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path
                  d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Upload MIDI File
            </Button>
          ) : (
            <div className="melody-input__file-info">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path
                  d="M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <polyline
                  points="13 2 13 9 20 9"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              <span>{midiFile.name}</span>
              <Button variant="ghost" size="sm" onClick={handleRemoveFile} disabled={disabled}>
                Remove
              </Button>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};
