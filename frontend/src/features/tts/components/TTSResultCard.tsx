/**
 * TTSResultCard Component
 *
 * Display TTS generation result with audio player and actions
 */

import { useState } from 'react';
import { Card, Button, Input, Modal } from '@/components/ui';
import { AudioPlayer } from '@/components/audio/AudioPlayer';
import { saveAsVoice } from '@/services/tts.service';
import { useToast } from '@/hooks/useToast';
import type { TTSResponse } from '@/types/tts.types';

interface TTSResultCardProps {
  result: TTSResponse;
  onReset: () => void;
}

export const TTSResultCard: React.FC<TTSResultCardProps> = ({ result, onReset }) => {
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [voiceName, setVoiceName] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const { showToast } = useToast();

  const handleDownload = () => {
    if (!result.output_file) return;

    const link = document.createElement('a');
    link.href = result.output_file;
    link.download = `tts_${Date.now()}.wav`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    showToast({ type: 'success', message: 'Audio downloaded successfully' });
  };

  const handleSaveAsVoice = async () => {
    if (!voiceName.trim() || !result.output_file) return;

    setIsSaving(true);
    try {
      await saveAsVoice(result.output_file, voiceName.trim());
      showToast({ type: 'success', message: 'Voice saved to library' });
      setShowSaveModal(false);
      setVoiceName('');
    } catch (error) {
      showToast({ type: 'error', message: 'Failed to save voice' });
    } finally {
      setIsSaving(false);
    }
  };

  if (!result.output_file) return null;

  return (
    <>
      <Card className="tts-result-card">
        <div className="tts-result-card__header">
          <h3>Generated Speech</h3>
          <Button variant="ghost" size="sm" onClick={onReset}>
            Generate New
          </Button>
        </div>

        <AudioPlayer
          src={result.output_file}
          className="tts-result-card__player"
        />

        <div className="tts-result-card__actions">
          <Button variant="primary" onClick={handleDownload}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Download
          </Button>

          <Button variant="outline" onClick={() => setShowSaveModal(true)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M17 21v-8H7v8M7 3v5h8"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Save as Voice
          </Button>
        </div>

        <div className="tts-result-card__info">
          <div className="tts-result-card__info-item">
            <span className="tts-result-card__info-label">Job ID:</span>
            <span className="tts-result-card__info-value">{result.job_id}</span>
          </div>
          <div className="tts-result-card__info-item">
            <span className="tts-result-card__info-label">Status:</span>
            <span className="tts-result-card__info-value status-completed">
              {result.status}
            </span>
          </div>
        </div>
      </Card>

      <Modal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        title="Save as Voice"
      >
        <div className="tts-result-card__save-modal">
          <p>Enter a name for this voice to add it to your library:</p>

          <Input
            type="text"
            placeholder="Voice name..."
            value={voiceName}
            onChange={(e) => setVoiceName(e.target.value)}
            maxLength={50}
            autoFocus
          />

          <div className="tts-result-card__save-modal-actions">
            <Button variant="outline" onClick={() => setShowSaveModal(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleSaveAsVoice}
              disabled={!voiceName.trim() || isSaving}
            >
              {isSaving ? 'Saving...' : 'Save Voice'}
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
};
