/**
 * VoiceTile Component
 *
 * Individual voice tile in the voice library grid
 */

import { Button } from '@/components/ui';
import type { VoiceProfile } from '@/types/tts.types';

interface VoiceTileProps {
  voice: VoiceProfile;
  isSelected: boolean;
  isPlaying: boolean;
  onSelect: () => void;
  onPreview: () => void;
}

export const VoiceTile: React.FC<VoiceTileProps> = ({
  voice,
  isSelected,
  isPlaying,
  onSelect,
  onPreview,
}) => {
  const formatDuration = (seconds?: number) => {
    if (!seconds) return '';
    return `${seconds.toFixed(1)}s`;
  };

  return (
    <div
      className={`voice-tile ${isSelected ? 'voice-tile--selected' : ''}`}
      onClick={onSelect}
    >
      <div className="voice-tile__header">
        <div className="voice-tile__icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 14a2 2 0 100-4 2 2 0 000 4z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M17.5 12a5.5 5.5 0 11-11 0 5.5 5.5 0 0111 0z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <span className="voice-tile__category">{voice.category}</span>
      </div>

      <div className="voice-tile__content">
        <h4 className="voice-tile__name">{voice.name}</h4>
        {voice.duration && (
          <span className="voice-tile__duration">{formatDuration(voice.duration)}</span>
        )}
      </div>

      <Button
        variant="outline"
        size="sm"
        onClick={(e) => {
          e.stopPropagation();
          onPreview();
        }}
        className="voice-tile__preview-btn"
      >
        {isPlaying ? (
          <>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="4" width="4" height="16" />
              <rect x="14" y="4" width="4" height="16" />
            </svg>
            Stop
          </>
        ) : (
          <>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
            Preview
          </>
        )}
      </Button>

      {isSelected && (
        <div className="voice-tile__selected-indicator">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" />
          </svg>
        </div>
      )}
    </div>
  );
};
