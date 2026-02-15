import React, { useState } from 'react';
import { Card } from '@/components';
import { Button } from '@/components';
import { StatusBadge } from '@/components';
import { jobService } from '@/services/job.service';
import type { JobDetailResponse } from '@/types/job.types';

interface ResultsCardProps {
  job: JobDetailResponse;
  onStartNew: () => void;
}

export const ResultsCard: React.FC<ResultsCardProps> = ({ job, onStartNew }) => {
  const [downloading, setDownloading] = useState<string | null>(null);

  // Check if this is an instrumental job
  const isInstrumentalJob = job.input_filename.startsWith('instrumental_');
  const isCompleteSongJob = job.input_filename.startsWith('complete_song_');

  const handleDownload = async (format: 'wav' | 'mp3' | 'mp4') => {
    try {
      setDownloading(format);
      const blob = await jobService.downloadResult(job.job_id, { format });

      const extension = format;
      const baseFilename = job.input_filename.replace(/\.[^/.]+$/, '');
      const filename = `${baseFilename}_replaced.${extension}`;

      jobService.downloadBlob(blob, filename);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download file. Please try again.');
    } finally {
      setDownloading(null);
    }
  };

  const handleInstrumentalDownload = async (outputType: 'instrumental_wav' | 'instrumental_mp3' | 'midi') => {
    try {
      setDownloading(outputType);
      const response = await fetch(`/api/music/generate-instrumental/${job.job_id}/download/${outputType}`);
      if (!response.ok) throw new Error('Download failed');

      const blob = await response.blob();
      const extension = outputType.includes('wav') ? 'wav' : outputType.includes('mp3') ? 'mp3' : 'mid';
      const filename = `${job.input_filename}_${outputType}.${extension}`;

      jobService.downloadBlob(blob, filename);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download file. Please try again.');
    } finally {
      setDownloading(null);
    }
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString();
  };

  return (
    <Card>
      <div className="results-card">
        <div className="results-card__header">
          <div className="results-card__status">
            <StatusBadge status="success">Processing Complete!</StatusBadge>
            <h2 className="results-card__title">Processing Complete!</h2>
          </div>
          <p className="results-card__subtitle">Your file is ready for download</p>
        </div>

        <div className="results-card__info">
          <div className="results-card__info-grid">
            <div className="results-card__info-item">
              <span className="results-card__info-label">Original File</span>
              <span className="results-card__info-value">{job.input_filename}</span>
            </div>
            <div className="results-card__info-item">
              <span className="results-card__info-label">Speakers Processed</span>
              <span className="results-card__info-value">{job.speakers.length}</span>
            </div>
            <div className="results-card__info-item">
              <span className="results-card__info-label">Completed At</span>
              <span className="results-card__info-value">{formatDate(job.created_at)}</span>
            </div>
            <div className="results-card__info-item">
              <span className="results-card__info-label">Job ID</span>
              <span className="results-card__info-value results-card__info-value--mono">
                {job.job_id}
              </span>
            </div>
          </div>
        </div>

        {(job.output_file || isInstrumentalJob || isCompleteSongJob) && (
          <div className="results-card__preview">
            <h3 className="results-card__preview-title">🎧 Audio Preview</h3>
            <audio
              className="results-card__audio-player"
              controls
              src={
                isInstrumentalJob
                  ? `/api/music/generate-instrumental/${job.job_id}/download/instrumental_wav`
                  : isCompleteSongJob
                  ? `/api/music/generate-song/${job.job_id}/download/mixed_song_wav`
                  : `/api/jobs/${job.job_id}/download?format=wav`
              }
            >
              Your browser does not support the audio element.
            </audio>
          </div>
        )}

        <div className="results-card__downloads">
          <h3 className="results-card__downloads-title">Download Options</h3>
          <div className="results-card__download-buttons">
            {isInstrumentalJob ? (
              <>
                <Button
                  variant="primary"
                  onClick={() => handleInstrumentalDownload('instrumental_wav')}
                  disabled={downloading !== null}
                >
                  {downloading === 'instrumental_wav' ? (
                    <span className="results-card__button-content">
                      <span className="results-card__spinner"></span>
                      Downloading...
                    </span>
                  ) : (
                    <span className="results-card__button-content">
                      <svg
                        className="results-card__button-icon"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                        />
                      </svg>
                      🎵 Instrumental (WAV)
                    </span>
                  )}
                </Button>

                <Button
                  variant="secondary"
                  onClick={() => handleInstrumentalDownload('instrumental_mp3')}
                  disabled={downloading !== null}
                >
                  {downloading === 'instrumental_mp3' ? (
                    <span className="results-card__button-content">
                      <span className="results-card__spinner"></span>
                      Downloading...
                    </span>
                  ) : (
                    <span className="results-card__button-content">
                      <svg
                        className="results-card__button-icon"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                        />
                      </svg>
                      🎵 Instrumental (MP3)
                    </span>
                  )}
                </Button>

                <Button
                  variant="secondary"
                  onClick={() => handleInstrumentalDownload('midi')}
                  disabled={downloading !== null}
                >
                  {downloading === 'midi' ? (
                    <span className="results-card__button-content">
                      <span className="results-card__spinner"></span>
                      Downloading...
                    </span>
                  ) : (
                    <span className="results-card__button-content">
                      <svg
                        className="results-card__button-icon"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                        />
                      </svg>
                      🎹 MIDI File
                    </span>
                  )}
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="primary"
                  onClick={() => handleDownload('wav')}
                  disabled={downloading !== null}
                >
                  {downloading === 'wav' ? (
                    <span className="results-card__button-content">
                      <span className="results-card__spinner"></span>
                      Downloading...
                    </span>
                  ) : (
                    <span className="results-card__button-content">
                      <svg
                        className="results-card__button-icon"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                        />
                      </svg>
                      Download WAV
                    </span>
                  )}
                </Button>

                <Button
                  variant="secondary"
                  onClick={() => handleDownload('mp3')}
                  disabled={downloading !== null}
                >
                  {downloading === 'mp3' ? (
                    <span className="results-card__button-content">
                      <span className="results-card__spinner"></span>
                      Downloading...
                    </span>
                  ) : (
                    <span className="results-card__button-content">
                      <svg
                        className="results-card__button-icon"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                        />
                      </svg>
                      Download MP3
                    </span>
                  )}
                </Button>

                {job.input_type === 'video' && (
                  <Button
                    variant="secondary"
                    onClick={() => handleDownload('mp4')}
                    disabled={downloading !== null}
                  >
                    {downloading === 'mp4' ? (
                      <span className="results-card__button-content">
                        <span className="results-card__spinner"></span>
                        Downloading...
                      </span>
                    ) : (
                      <span className="results-card__button-content">
                        <svg
                          className="results-card__button-icon"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                          />
                        </svg>
                        Download MP4
                      </span>
                    )}
                  </Button>
                )}
              </>
            )}
          </div>
        </div>

        <div className="results-card__actions">
          <Button variant="outline" onClick={onStartNew} fullWidth>
            Process Another File
          </Button>
        </div>
      </div>
    </Card>
  );
};
