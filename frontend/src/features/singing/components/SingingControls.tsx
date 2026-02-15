/**
 * Singing Controls Component
 *
 * Tempo and key shift sliders with labels
 */

import React from 'react';
import { Card } from '@/components/ui';
import { SINGING_HELP_TEXT } from '@/types/singing.types';

interface SingingControlsProps {
  tempo: number;
  keyShift: number;
  onTempoChange: (tempo: number) => void;
  onKeyShiftChange: (shift: number) => void;
  disabled?: boolean;
}

export const SingingControls: React.FC<SingingControlsProps> = ({
  tempo,
  keyShift,
  onTempoChange,
  onKeyShiftChange,
  disabled,
}) => {
  return (
    <Card className="singing-controls">
      <div className="singing-controls__header">
        <h3>Step 4: Adjust Parameters</h3>
      </div>

      {/* Tempo Control */}
      <div className="singing-controls__control">
        <div className="singing-controls__label">
          <label htmlFor="tempo-slider">Tempo</label>
          <span className="singing-controls__value">{tempo} BPM</span>
        </div>
        <p className="singing-controls__help">{SINGING_HELP_TEXT.tempo}</p>
        <div className="singing-controls__slider-container">
          <input
            id="tempo-slider"
            type="range"
            min="60"
            max="200"
            step="1"
            value={tempo}
            onChange={(e) => onTempoChange(Number(e.target.value))}
            disabled={disabled}
            className="singing-controls__slider"
          />
          <div className="singing-controls__marks">
            <span>60</span>
            <span>120</span>
            <span>200</span>
          </div>
        </div>
      </div>

      {/* Key Shift Control */}
      <div className="singing-controls__control">
        <div className="singing-controls__label">
          <label htmlFor="keyshift-slider">Key Shift</label>
          <span className="singing-controls__value">
            {keyShift > 0 ? '+' : ''}
            {keyShift} semitones
          </span>
        </div>
        <p className="singing-controls__help">{SINGING_HELP_TEXT.keyShift}</p>
        <div className="singing-controls__slider-container">
          <input
            id="keyshift-slider"
            type="range"
            min="-12"
            max="12"
            step="1"
            value={keyShift}
            onChange={(e) => onKeyShiftChange(Number(e.target.value))}
            disabled={disabled}
            className="singing-controls__slider"
          />
          <div className="singing-controls__marks">
            <span>-12</span>
            <span>0</span>
            <span>+12</span>
          </div>
        </div>
      </div>
    </Card>
  );
};
