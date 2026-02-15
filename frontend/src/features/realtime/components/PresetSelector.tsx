/**
 * PresetSelector Component
 *
 * Voice effect preset selector with quick-switch buttons
 */

import React from 'react';
import type { VoicePreset } from '../types';

interface PresetSelectorProps {
  presets: VoicePreset[];
  selectedPresetId: string | null;
  onSelectPreset: (presetId: string) => void;
  disabled?: boolean;
}

export const PresetSelector: React.FC<PresetSelectorProps> = ({
  presets,
  selectedPresetId,
  onSelectPreset,
  disabled = false,
}) => {
  return (
    <div className="preset-selector">
      <h3 className="preset-selector__title">Voice Presets</h3>
      <p className="preset-selector__description">
        Quick-switch between voice effects
      </p>

      <div className="preset-selector__grid">
        {presets.map((preset) => {
          const isSelected = selectedPresetId === preset.id;

          return (
            <button
              key={preset.id}
              className={`preset-selector__button ${
                isSelected ? 'preset-selector__button--selected' : ''
              }`}
              onClick={() => onSelectPreset(preset.id)}
              disabled={disabled}
              title={preset.description}
            >
              <span className="preset-selector__icon">{preset.icon}</span>
              <span className="preset-selector__name">{preset.name}</span>
              {isSelected && (
                <span className="preset-selector__check">✓</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
