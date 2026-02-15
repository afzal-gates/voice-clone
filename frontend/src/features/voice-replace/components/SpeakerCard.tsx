import React, { useState } from 'react';
import { Card } from '@/components';
import { Button } from '@/components';
import type { Speaker, Voice } from '@/types/job.types';

interface SpeakerCardProps {
  speaker: Speaker;
  voices: Voice[];
  assignedVoiceRef?: string;
  onAssign: (speakerId: string, voiceRef: string) => void;
  disabled?: boolean;
}

export const SpeakerCard: React.FC<SpeakerCardProps> = ({
  speaker,
  voices,
  assignedVoiceRef,
  onAssign,
  disabled = false
}) => {
  const [selectedVoice, setSelectedVoice] = useState<string>(assignedVoiceRef || '');

  const handleVoiceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedVoice(e.target.value);
  };

  const handleAssign = () => {
    if (selectedVoice) {
      onAssign(speaker.speaker_id, selectedVoice);
    }
  };

  const formatDuration = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const isAssigned = !!assignedVoiceRef;

  return (
    <Card>
      <div className="speaker-card">
        <div className="speaker-card__header">
          <div className="speaker-card__avatar">
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="speaker-card__info">
            <h3 className="speaker-card__label">{speaker.label}</h3>
            <div className="speaker-card__meta">
              <span className="speaker-card__meta-item">
                {speaker.segment_count} segments
              </span>
              <span className="speaker-card__meta-separator">•</span>
              <span className="speaker-card__meta-item">
                {formatDuration(speaker.total_duration)}
              </span>
            </div>
          </div>
          {isAssigned && (
            <div className="speaker-card__badge speaker-card__badge--success">
              <svg
                className="speaker-card__badge-icon"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
              Assigned
            </div>
          )}
        </div>

        <div className="speaker-card__content">
          <div className="speaker-card__field">
            <label htmlFor={`voice-${speaker.speaker_id}`} className="speaker-card__label-text">
              Select Voice
            </label>
            <select
              id={`voice-${speaker.speaker_id}`}
              className="speaker-card__select"
              value={selectedVoice}
              onChange={handleVoiceChange}
              disabled={disabled}
            >
              <option value="">-- Choose a voice --</option>
              {voices.map((voice) => (
                <option key={voice.id} value={voice.id}>
                  {voice.name} ({voice.language}
                  {voice.gender ? `, ${voice.gender}` : ''})
                </option>
              ))}
            </select>
          </div>

          <div className="speaker-card__actions">
            <Button
              variant={isAssigned ? 'secondary' : 'primary'}
              onClick={handleAssign}
              disabled={!selectedVoice || disabled}
              fullWidth
            >
              {isAssigned ? 'Update Assignment' : 'Assign Voice'}
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
};
