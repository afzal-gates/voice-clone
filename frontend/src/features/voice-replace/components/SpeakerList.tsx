import React from 'react';
import { Card } from '@/components';
import { Button } from '@/components';
import { SpeakerCard } from './SpeakerCard';
import type { Speaker, Voice } from '@/types/job.types';

interface SpeakerListProps {
  speakers: Speaker[];
  voices: Voice[];
  loadingVoices: boolean;
  assignments: Map<string, string>;
  onAssign: (speakerId: string, voiceRef: string) => void;
  onSubmit: () => void;
  submitting: boolean;
  allAssigned: boolean;
}

export const SpeakerList: React.FC<SpeakerListProps> = ({
  speakers,
  voices,
  loadingVoices,
  assignments,
  onAssign,
  onSubmit,
  submitting,
  allAssigned
}) => {
  return (
    <div className="speaker-list">
      <Card>
        <div className="speaker-list__header">
          <h2 className="speaker-list__title">Assign Voices to Speakers</h2>
          <p className="speaker-list__description">
            We detected {speakers.length} speaker{speakers.length !== 1 ? 's' : ''} in your file.
            Please assign a voice to each speaker.
          </p>
          <div className="speaker-list__progress">
            <span className="speaker-list__progress-text">
              {assignments.size} of {speakers.length} assigned
            </span>
            <div className="speaker-list__progress-bar">
              <div
                className="speaker-list__progress-fill"
                style={{ width: `${(assignments.size / speakers.length) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </Card>

      {loadingVoices ? (
        <Card>
          <div className="speaker-list__loading">
            <div className="speaker-list__spinner"></div>
            <p>Loading available voices...</p>
          </div>
        </Card>
      ) : (
        <div className="speaker-list__items">
          {speakers.map((speaker) => (
            <SpeakerCard
              key={speaker.speaker_id}
              speaker={speaker}
              voices={voices}
              assignedVoiceRef={assignments.get(speaker.speaker_id)}
              onAssign={onAssign}
              disabled={submitting}
            />
          ))}
        </div>
      )}

      <Card>
        <div className="speaker-list__actions">
          <Button
            variant="primary"
            onClick={onSubmit}
            disabled={!allAssigned || submitting}
            fullWidth
          >
            {submitting ? 'Processing...' : 'Continue with Voice Replacement'}
          </Button>
          {!allAssigned && (
            <p className="speaker-list__warning">
              Please assign voices to all speakers before continuing
            </p>
          )}
        </div>
      </Card>
    </div>
  );
};
