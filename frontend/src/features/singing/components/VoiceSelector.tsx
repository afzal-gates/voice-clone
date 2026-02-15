/**
 * Voice Selector Component
 *
 * Dropdown selector for singing voice models
 */

import React from 'react';
import { Card } from '@/components/ui';
import type { SingingVoiceModel } from '@/types/singing.types';
import { SINGING_HELP_TEXT } from '@/types/singing.types';

interface VoiceSelectorProps {
  voices: SingingVoiceModel[];
  selectedVoice: string | null;
  onChange: (voiceId: string) => void;
  disabled?: boolean;
}

export const VoiceSelector: React.FC<VoiceSelectorProps> = ({
  voices,
  selectedVoice,
  onChange,
  disabled,
}) => {
  return (
    <Card className="voice-selector">
      <div className="voice-selector__header">
        <h3>Step 3: Select Voice Model</h3>
      </div>

      <p className="voice-selector__help">{SINGING_HELP_TEXT.voice}</p>

      <select
        value={selectedVoice || ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled || voices.length === 0}
        className="voice-selector__select"
      >
        <option value="" disabled>
          {voices.length === 0 ? 'Loading voices...' : 'Select a voice model'}
        </option>
        {voices.map((voice) => (
          <option key={voice.model_id} value={voice.model_id}>
            {voice.name} ({voice.language})
          </option>
        ))}
      </select>

      {selectedVoice && (
        <div className="voice-selector__info">
          {voices.find((v) => v.model_id === selectedVoice)?.description && (
            <p className="voice-selector__description">
              {voices.find((v) => v.model_id === selectedVoice)?.description}
            </p>
          )}
        </div>
      )}
    </Card>
  );
};
