/**
 * Singing Result Component
 *
 * Audio player with download options
 */

import React from 'react';
import { Card, Button } from '@/components/ui';
import { AudioPlayer } from '@/components/audio/AudioPlayer';
import type { SingingResponse } from '@/types/singing.types';
import { downloadSinging } from '@/services/singing.service';
import { API_BASE_URL } from '@/config/api.config';

interface SingingResultProps {
  result: SingingResponse;
  onReset: () => void;
}

export const SingingResult: React.FC<SingingResultProps> = ({ result, onReset }) => {
  const audioUrl = result.output_file
    ? `${API_BASE_URL}${result.output_file}`
    : undefined;

  const handleDownload = (format: 'wav' | 'mp3') => {
    const url = downloadSinging(result.job_id, format);
    const link = document.createElement('a');
    link.href = url;
    link.download = `singing_${result.job_id}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <Card className="singing-result">
      <div className="singing-result__header">
        <h3>Singing Generated!</h3>
        {result.duration && (
          <span className="singing-result__duration">{result.duration.toFixed(2)}s</span>
        )}
      </div>

      {audioUrl && (
        <div className="singing-result__player">
          <AudioPlayer src={audioUrl} />
        </div>
      )}

      <div className="singing-result__actions">
        <div className="singing-result__downloads">
          <Button variant="primary" onClick={() => handleDownload('wav')}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Download WAV
          </Button>
          <Button variant="secondary" onClick={() => handleDownload('mp3')}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path
                d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Download MP3
          </Button>
        </div>
        <Button variant="ghost" onClick={onReset}>
          Generate Another
        </Button>
      </div>

      <div className="singing-result__info">
        <p className="singing-result__job-id">
          Job ID: <code>{result.job_id}</code>
        </p>
      </div>
    </Card>
  );
};
