/**
 * Voice Tile Component
 *
 * Individual voice selection tile
 */

import React from 'react';
import type { VoiceProfile } from '@/types/realtime.types';

interface VoiceTileProps {
  voice: VoiceProfile;
  selected: boolean;
  onSelect: (voiceId: string) => void;
  disabled?: boolean;
}

export const VoiceTile: React.FC<VoiceTileProps> = ({
  voice,
  selected,
  onSelect,
  disabled = false,
}) => {
  return (
    <button
      className={`voice-tile ${selected ? 'voice-tile--selected' : ''} ${
        disabled ? 'voice-tile--disabled' : ''
      }`}
      onClick={() => !disabled && onSelect(voice.id)}
      disabled={disabled}
    >
      <div className="voice-tile__icon">
        <svg fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
          <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
        </svg>
      </div>

      <div className="voice-tile__content">
        <h4 className="voice-tile__name">{voice.name}</h4>
        {voice.description && (
          <p className="voice-tile__description">{voice.description}</p>
        )}
        <span className="voice-tile__category">{voice.category}</span>
      </div>

      {selected && (
        <div className="voice-tile__checkmark">
          <svg fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        </div>
      )}
    </button>
  );
};
